package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/sandbox"
	"golang.org/x/sys/unix"
)

const (
	captureTimeout               = 45 * time.Second
	chromiumLauncherPath         = "/usr/bin/chromium"
	chromiumLauncherSHA256       = "2c8d32d29dc6781c35ae196ea83299d507ac88fc339301abe74672feda299779"
	restrictedRendererPATH       = "/usr/local/bin:/usr/bin:/bin"
	runtimeWorkRoot              = "/work"
	rendererUnavailableChildExit = 4
	fixedZshStartup              = "PROMPT='demo > '\nRPROMPT=''\nPROMPT_EOL_MARK=''\nunsetopt promptsubst\nsetopt no_beep\n"
)

var privateRuntimeDirectories = []string{
	"home",
	"zdotdir",
	"cache",
	"config",
	"data",
	"runtime",
	"tmp",
	"demo",
	"eza-config",
}

// Rod v0.116.2 tests these Linux candidates in this order. The final name must
// resolve to the preflighted immutable launcher; every earlier candidate must
// remain absent so Rod cannot select a different browser.
var rodLinuxBrowserCandidatesThroughChromium = []string{
	"chrome",
	"google-chrome",
	"/usr/bin/google-chrome",
	"microsoft-edge",
	"/usr/bin/microsoft-edge",
	"chromium",
}

type browserPreflightConfig struct {
	target         string
	expectedSHA256 string
	lookPath       func(string) (string, error)
}

type captureDependencies struct {
	browserPreflight func() error
	prepareRuntime   func() error
	changeDirectory  func(string) error
	vhsPath          string
	execRestricted   func(sandbox.ExecSpec) error
}

type restrictedChildRunner func(context.Context, sandbox.Child) (sandbox.Outcome, error)

func main() {
	os.Exit(run(os.Args[1:], os.Stdout, os.Stderr))
}

func run(args []string, stdout, stderr io.Writer) int {
	var err error
	switch {
	case len(args) == 2 && args[0] == "__capture":
		err = capture(args[1])
	case len(args) == 1 && args[0] == "--self-test":
		err = selfTest(stdout)
	default:
		err = failure.E(failure.InvalidContract, failure.StageInput, "", failure.RuleInputRef, errors.New("unsupported invocation"))
	}
	if err == nil {
		return 0
	}
	fmt.Fprintln(stderr, err)
	return failure.ExitCode(err)
}

func capture(tape string) error {
	return captureWith(tape, captureDependencies{
		browserPreflight: preflightBrowser,
		prepareRuntime:   prepareRuntimeDirectories,
		changeDirectory:  os.Chdir,
		vhsPath:          "/usr/local/bin/vhs",
		execRestricted:   sandbox.ExecRestricted,
	})
}

func captureWith(tape string, dependencies captureDependencies) error {
	if dependencies.browserPreflight == nil || dependencies.prepareRuntime == nil ||
		dependencies.changeDirectory == nil || dependencies.vhsPath == "" || dependencies.execRestricted == nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, errors.New("capture dependency unavailable"))
	}
	if err := dependencies.browserPreflight(); err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}
	if err := dependencies.prepareRuntime(); err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}
	if err := dependencies.changeDirectory("/work/demo"); err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}

	spec := sandbox.ExecSpec{
		Path: dependencies.vhsPath,
		Args: []string{dependencies.vhsPath, tape},
		Env:  vhsExecEnvironment(),
		Policy: sandbox.Policy{
			ReadOnlyPaths:  existingDirectories("/usr", "/etc", "/proc", "/sys", "/dev"),
			ReadWritePaths: existingDirectories("/tmp", "/work", "/dev/shm"),
		},
	}
	if err := dependencies.execRestricted(spec); err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}
	return nil
}

func selfTestChildOutcome(child sandbox.Child, runChild restrictedChildRunner) error {
	if runChild == nil {
		return failure.E(failure.ExecutionFailed, failure.StageCapture, "", failure.RuleCaptureFailed, errors.New("restricted child runner unavailable"))
	}
	outcome, err := runChild(context.Background(), child)
	return mapChildOutcome(outcome, err)
}

func mapChildOutcome(outcome sandbox.Outcome, childErr error) error {
	if outcome.TimedOut || errors.Is(childErr, sandbox.ErrProcessTimeout) {
		return failure.E(failure.ExecutionFailed, failure.StageCapture, "", failure.RuleCaptureTimeout, errors.New("restricted child timed out"))
	}
	if childErr != nil {
		return failure.E(failure.ExecutionFailed, failure.StageCapture, "", failure.RuleCaptureFailed, errors.New("restricted child cleanup failed"))
	}
	if outcome.Exited && outcome.ExitCode == 0 {
		return nil
	}
	if outcome.Exited && outcome.ExitCode == rendererUnavailableChildExit {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, errors.New("restricted renderer unavailable"))
	}
	return failure.E(failure.ExecutionFailed, failure.StageCapture, "", failure.RuleCaptureFailed, errors.New("restricted capture failed"))
}

func preflightBrowser() error {
	return validateBrowser(browserPreflightConfig{
		target:         chromiumLauncherPath,
		expectedSHA256: chromiumLauncherSHA256,
		lookPath:       lookPathInRendererPath,
	})
}

func validateBrowser(config browserPreflightConfig) error {
	if config.target == "" || config.expectedSHA256 == "" || config.lookPath == nil {
		return errors.New("invalid browser preflight configuration")
	}

	last := len(rodLinuxBrowserCandidatesThroughChromium) - 1
	for index, candidate := range rodLinuxBrowserCandidatesThroughChromium {
		resolved, err := config.lookPath(candidate)
		if index != last {
			if err == nil {
				return fmt.Errorf("earlier browser candidate available: %s", candidate)
			}
			if !errors.Is(err, exec.ErrNotFound) {
				return fmt.Errorf("inspect earlier browser candidate: %w", err)
			}
			continue
		}
		if err != nil {
			return fmt.Errorf("resolve Chromium launcher: %w", err)
		}
		if filepath.Clean(resolved) != filepath.Clean(config.target) {
			return errors.New("Chromium launcher resolved to an unexpected path")
		}
	}

	return validatePinnedLauncher(config.target, config.expectedSHA256)
}

func lookPathInRendererPath(name string) (string, error) {
	if strings.ContainsRune(name, os.PathSeparator) {
		return executableCandidate(name)
	}
	for _, directory := range filepath.SplitList(restrictedRendererPATH) {
		candidate := filepath.Join(directory, name)
		resolved, err := executableCandidate(candidate)
		if err == nil {
			return resolved, nil
		}
		if !errors.Is(err, exec.ErrNotFound) {
			return "", err
		}
	}
	return "", exec.ErrNotFound
}

func executableCandidate(path string) (string, error) {
	info, err := os.Stat(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return "", exec.ErrNotFound
		}
		return "", err
	}
	if info.IsDir() || info.Mode().Perm()&0o111 == 0 {
		return "", exec.ErrNotFound
	}
	return path, nil
}

func validatePinnedLauncher(path, expectedSHA256 string) error {
	var before unix.Stat_t
	if err := unix.Fstatat(unix.AT_FDCWD, path, &before, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fmt.Errorf("inspect Chromium launcher: %w", err)
	}
	if before.Mode&unix.S_IFMT != unix.S_IFREG {
		return errors.New("Chromium launcher is not a regular file")
	}
	if before.Uid != 0 {
		return errors.New("Chromium launcher is not root-owned")
	}
	if before.Mode&0o7777 != 0o755 {
		return errors.New("Chromium launcher mode is not 0755")
	}

	fd, err := unix.Open(path, unix.O_RDONLY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("open Chromium launcher without following links: %w", err)
	}
	file := os.NewFile(uintptr(fd), "chromium-launcher")
	if file == nil {
		_ = unix.Close(fd)
		return errors.New("open Chromium launcher")
	}

	var opened unix.Stat_t
	if err := unix.Fstat(fd, &opened); err != nil {
		_ = file.Close()
		return fmt.Errorf("inspect opened Chromium launcher: %w", err)
	}
	if before.Dev != opened.Dev || before.Ino != opened.Ino || before.Mode != opened.Mode || before.Uid != opened.Uid {
		_ = file.Close()
		return errors.New("Chromium launcher changed during preflight")
	}

	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		_ = file.Close()
		return fmt.Errorf("hash Chromium launcher: %w", err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("close Chromium launcher: %w", err)
	}
	if got := fmt.Sprintf("%x", hasher.Sum(nil)); got != expectedSHA256 {
		return errors.New("Chromium launcher checksum mismatch")
	}
	return nil
}

func selfTest(stdout io.Writer) error {
	if os.Geteuid() == 0 {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, errors.New("root runtime"))
	}
	for _, tool := range []string{"vhs", "ttyd", "chromium", "fc-match", "zsh", "ffmpeg"} {
		if _, err := exec.LookPath(tool); err != nil {
			return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
		}
	}
	font, err := exec.Command("fc-match", "JetBrains Mono").Output()
	if err != nil || !bytes.Contains(bytes.ToLower(font), []byte("jetbrains")) {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, errors.New("font unavailable"))
	}
	if connection, err := net.DialTimeout("tcp", "1.1.1.1:443", 500*time.Millisecond); err == nil {
		_ = connection.Close()
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, errors.New("network egress available"))
	}
	if _, err := os.ReadFile("/landlock-denied/readable"); err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}

	executable, err := os.Executable()
	if err != nil {
		return failure.E(failure.RendererUnavailable, failure.StageRuntime, "", failure.RuleRuntimeUnavailable, err)
	}
	tape := "/usr/local/share/readme-terminal-demo/smoke.tape"
	var childOutput bytes.Buffer
	err = selfTestChildOutcome(sandbox.Child{
		Path:    executable,
		Args:    []string{"__capture", tape},
		Env:     captureHelperEnvironment(),
		Dir:     "/work",
		Stdout:  &childOutput,
		Stderr:  &childOutput,
		Timeout: captureTimeout,
	}, sandbox.RunRestrictedChild)
	if err != nil {
		return err
	}
	media := "/work/smoke.gif"
	info, err := os.Stat(media)
	if err != nil || info.Size() == 0 {
		return failure.E(failure.ExecutionFailed, failure.StageMedia, "", failure.RuleMediaInvalid, err)
	}
	fmt.Fprintln(stdout, "readme-terminal-demo self-test ok")
	return nil
}

func prepareRuntimeDirectories() error {
	return prepareRuntimeDirectoriesAt(runtimeWorkRoot)
}

func prepareRuntimeDirectoriesAt(root string) error {
	if root == "" || !filepath.IsAbs(root) || filepath.Clean(root) != root {
		return errors.New("invalid runtime root")
	}

	rootFD, err := unix.Open(root, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("open private runtime root: %w", err)
	}
	defer unix.Close(rootFD)
	if err := requireOwnedPrivateDirectory(rootFD); err != nil {
		return fmt.Errorf("validate private runtime root: %w", err)
	}

	for _, name := range privateRuntimeDirectories {
		fd, err := ensurePrivateDirectoryAt(rootFD, name)
		if err != nil {
			return err
		}
		if err := unix.Close(fd); err != nil {
			return fmt.Errorf("close private runtime directory: %w", err)
		}
	}

	ezaFD, err := openPrivateDirectoryAt(rootFD, "eza-config")
	if err != nil {
		return err
	}
	if err := requireEmptyDirectory(ezaFD); err != nil {
		_ = unix.Close(ezaFD)
		return fmt.Errorf("validate empty eza configuration: %w", err)
	}
	if err := unix.Close(ezaFD); err != nil {
		return fmt.Errorf("close empty eza configuration: %w", err)
	}

	zdotdirFD, err := openPrivateDirectoryAt(rootFD, "zdotdir")
	if err != nil {
		return err
	}
	defer unix.Close(zdotdirFD)
	if err := writePrivateFileAt(zdotdirFD, ".zshrc", []byte(fixedZshStartup)); err != nil {
		return fmt.Errorf("write fixed zsh startup: %w", err)
	}
	return nil
}

func ensurePrivateDirectoryAt(parentFD int, name string) (int, error) {
	if name == "" || name == "." || name == ".." || strings.ContainsRune(name, os.PathSeparator) {
		return -1, errors.New("invalid private runtime directory name")
	}
	if err := unix.Mkdirat(parentFD, name, 0o700); err != nil && !errors.Is(err, unix.EEXIST) {
		return -1, fmt.Errorf("create private runtime directory: %w", err)
	}
	fd, err := openPrivateDirectoryAt(parentFD, name)
	if err != nil {
		return -1, err
	}
	if err := unix.Fchmod(fd, 0o700); err != nil {
		_ = unix.Close(fd)
		return -1, fmt.Errorf("set private runtime directory mode: %w", err)
	}
	return fd, nil
}

func openPrivateDirectoryAt(parentFD int, name string) (int, error) {
	fd, err := unix.Openat(parentFD, name, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return -1, fmt.Errorf("open private runtime directory: %w", err)
	}
	if err := requireOwnedDirectory(fd); err != nil {
		_ = unix.Close(fd)
		return -1, fmt.Errorf("validate private runtime directory: %w", err)
	}
	return fd, nil
}

func requireOwnedPrivateDirectory(fd int) error {
	if err := requireOwnedDirectory(fd); err != nil {
		return err
	}
	var stat unix.Stat_t
	if err := unix.Fstat(fd, &stat); err != nil {
		return err
	}
	if stat.Mode&0o7777 != 0o700 {
		return errors.New("runtime root mode is not 0700")
	}
	return nil
}

func requireOwnedDirectory(fd int) error {
	var stat unix.Stat_t
	if err := unix.Fstat(fd, &stat); err != nil {
		return err
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFDIR {
		return errors.New("runtime path is not a directory")
	}
	if int(stat.Uid) != os.Geteuid() || int(stat.Gid) != os.Getegid() {
		return errors.New("runtime directory has unexpected ownership")
	}
	return nil
}

func requireEmptyDirectory(fd int) error {
	duplicate, err := unix.Dup(fd)
	if err != nil {
		return err
	}
	directory := os.NewFile(uintptr(duplicate), "eza-config")
	if directory == nil {
		_ = unix.Close(duplicate)
		return errors.New("open eza configuration directory")
	}
	entries, readErr := directory.ReadDir(1)
	closeErr := directory.Close()
	if len(entries) != 0 {
		return errors.New("eza configuration directory is not empty")
	}
	if readErr != nil && !errors.Is(readErr, io.EOF) {
		return readErr
	}
	return closeErr
}

func writePrivateFileAt(parentFD int, name string, content []byte) error {
	flags := unix.O_WRONLY | unix.O_CLOEXEC | unix.O_NOFOLLOW | unix.O_NONBLOCK
	fd, err := unix.Openat(parentFD, name, flags|unix.O_CREAT|unix.O_EXCL, 0o600)
	if errors.Is(err, unix.EEXIST) {
		fd, err = unix.Openat(parentFD, name, flags, 0)
	}
	if err != nil {
		return err
	}
	defer unix.Close(fd)

	var stat unix.Stat_t
	if err := unix.Fstat(fd, &stat); err != nil {
		return err
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFREG || stat.Nlink != 1 {
		return errors.New("private runtime file is not a unique regular file")
	}
	if int(stat.Uid) != os.Geteuid() || int(stat.Gid) != os.Getegid() {
		return errors.New("private runtime file has unexpected ownership")
	}
	if err := unix.Fchmod(fd, 0o600); err != nil {
		return err
	}
	if err := unix.Ftruncate(fd, 0); err != nil {
		return err
	}
	for len(content) != 0 {
		written, err := unix.Write(fd, content)
		if errors.Is(err, unix.EINTR) {
			continue
		}
		if err != nil {
			return err
		}
		if written == 0 {
			return io.ErrShortWrite
		}
		content = content[written:]
	}
	return nil
}

func captureHelperEnvironment() []string {
	return []string{
		"PATH=/usr/local/bin:/usr/bin:/bin",
		"PWD=/work/demo",
		"HOME=/work/home",
		"ZDOTDIR=/work/zdotdir",
		"XDG_CACHE_HOME=/work/cache",
		"XDG_CONFIG_HOME=/work/config",
		"XDG_DATA_HOME=/work/data",
		"XDG_RUNTIME_DIR=/work/runtime",
		"TMPDIR=/work/tmp",
		"LANG=C.UTF-8",
		"LC_ALL=C.UTF-8",
		"TZ=UTC",
		"TERM=xterm-256color",
		"COLORTERM=truecolor",
		"USER=demo",
		"LOGNAME=demo",
		"SHELL=/usr/bin/zsh",
		"PAGER=cat",
		"GIT_PAGER=cat",
		"GIT_CONFIG_NOSYSTEM=1",
		"GIT_CONFIG_GLOBAL=/dev/null",
		"HISTFILE=/dev/null",
		"SOURCE_DATE_EPOCH=946684800",
		"FONTCONFIG_FILE=/etc/fonts/fonts.conf",
		"FONTCONFIG_PATH=/etc/fonts",
		"EZA_CONFIG_DIR=/work/eza-config",
		"EZA_COLORS=",
		"LS_COLORS=",
	}
}

func vhsExecEnvironment() []string {
	return []string{
		"PATH=/usr/local/bin:/usr/bin:/bin",
		"PWD=/work/demo",
		"HOME=/work/home",
		"ZDOTDIR=/work/zdotdir",
		"XDG_CACHE_HOME=/work/cache",
		"XDG_CONFIG_HOME=/work/config",
		"XDG_DATA_HOME=/work/data",
		"XDG_RUNTIME_DIR=/work/runtime",
		"TMPDIR=/work/tmp",
		"LANG=C.UTF-8",
		"LC_ALL=C.UTF-8",
		"TZ=UTC",
		"TERM=xterm-256color",
		"COLORTERM=truecolor",
		"USER=demo",
		"LOGNAME=demo",
		"SHELL=/usr/bin/zsh",
		"PAGER=cat",
		"GIT_PAGER=cat",
		"GIT_CONFIG_NOSYSTEM=1",
		"GIT_CONFIG_GLOBAL=/dev/null",
		"HISTFILE=/dev/null",
		"SOURCE_DATE_EPOCH=946684800",
		"VHS_NO_SANDBOX=1",
		"FONTCONFIG_FILE=/etc/fonts/fonts.conf",
		"FONTCONFIG_PATH=/etc/fonts",
		"EZA_CONFIG_DIR=/work/eza-config",
		"EZA_COLORS=",
		"LS_COLORS=",
	}
}

func existingDirectories(paths ...string) []string {
	result := make([]string, 0, len(paths))
	for _, path := range paths {
		info, err := os.Stat(path)
		if err == nil && info.IsDir() {
			result = append(result, filepath.Clean(path))
		}
	}
	return result
}
