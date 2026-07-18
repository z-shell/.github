package main

import (
	"context"
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/sandbox"
	"golang.org/x/sys/unix"
)

const testUnsupportedLandlockCapture = "README_TERMINAL_DEMO_TEST_UNSUPPORTED_CAPTURE"

func TestReservedChildExitMapping(t *testing.T) {
	tests := reservedChildOutcomeCases()
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			err := mapChildOutcome(test.outcome, nil)
			assertChildOutcomeMapping(t, err, test.wantClass, test.wantMessage)
		})
	}
}

func TestSelfTestMapsChildOutcome(t *testing.T) {
	wantChild := sandbox.Child{
		Path: "/trusted/readme-terminal-demo",
		Args: []string{"__capture", "/trusted/smoke.tape"},
		Dir:  "/work",
	}
	for _, test := range reservedChildOutcomeCases() {
		t.Run(test.name, func(t *testing.T) {
			called := false
			err := selfTestChildOutcome(wantChild, func(ctx context.Context, gotChild sandbox.Child) (sandbox.Outcome, error) {
				called = true
				if ctx == nil {
					t.Fatal("self-test child runner received a nil context")
				}
				if !reflect.DeepEqual(gotChild, wantChild) {
					t.Fatalf("self-test child = %#v, want %#v", gotChild, wantChild)
				}
				return test.outcome, nil
			})
			if !called {
				t.Fatal("self-test child runner was not called")
			}
			assertChildOutcomeMapping(t, err, test.wantClass, test.wantMessage)
		})
	}
}

type reservedChildOutcomeCase struct {
	name        string
	outcome     sandbox.Outcome
	wantClass   failure.Class
	wantMessage string
}

func reservedChildOutcomeCases() []reservedChildOutcomeCase {
	return []reservedChildOutcomeCase{
		{name: "normal-exit-zero", outcome: sandbox.Outcome{Exited: true, ExitCode: 0}},
		{
			name:        "VHS-normal-exit-one",
			outcome:     sandbox.Outcome{Exited: true, ExitCode: 1},
			wantClass:   failure.ExecutionFailed,
			wantMessage: "execution-failed: capture (capture.failed)",
		},
		{
			name:        "launcher-normal-exit-four",
			outcome:     sandbox.Outcome{Exited: true, ExitCode: 4},
			wantClass:   failure.RendererUnavailable,
			wantMessage: "renderer-unavailable: runtime (runtime.unavailable)",
		},
		{
			name:        "launcher-normal-exit-five",
			outcome:     sandbox.Outcome{Exited: true, ExitCode: 5},
			wantClass:   failure.ExecutionFailed,
			wantMessage: "execution-failed: capture (capture.failed)",
		},
		{
			name:        "signal-four-is-not-exit-four",
			outcome:     sandbox.Outcome{Signaled: true, Signal: unix.Signal(4)},
			wantClass:   failure.ExecutionFailed,
			wantMessage: "execution-failed: capture (capture.failed)",
		},
		{
			name:        "signal-five-is-not-exit-five",
			outcome:     sandbox.Outcome{Signaled: true, Signal: unix.Signal(5)},
			wantClass:   failure.ExecutionFailed,
			wantMessage: "execution-failed: capture (capture.failed)",
		},
	}
}

func assertChildOutcomeMapping(t *testing.T, err error, wantClass failure.Class, wantMessage string) {
	t.Helper()

	if wantClass == "" {
		if err != nil {
			t.Fatalf("mapped child outcome error = %v, want nil", err)
		}
		return
	}
	if got := failure.Classify(err); got != wantClass {
		t.Fatalf("mapped child class = %q, want %q", got, wantClass)
	}
	if got := err.Error(); got != wantMessage {
		t.Fatalf("mapped child message = %q, want %q", got, wantMessage)
	}
}

func TestCaptureHelperEnvironmentMatchesLiteralAllowlist(t *testing.T) {
	t.Setenv("HTTPS_PROXY", "http://hostile.invalid")
	t.Setenv("GITHUB_TOKEN", "must-not-leak")
	t.Setenv("CHROME_BIN", "/tmp/host-browser")
	t.Setenv("CHROME_DEVEL_SANDBOX", "/tmp/host-sandbox")
	t.Setenv("HOME", "/tmp/host-home")

	want := literalRendererEnvironment(false)
	got := captureHelperEnvironment()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("capture helper environment = %#v, want exact ordered allowlist %#v", got, want)
	}
	assertEnvironmentExcludesHostState(t, got)
}

func TestVHSExecEnvironmentMatchesLiteralAllowlist(t *testing.T) {
	t.Setenv("HTTPS_PROXY", "http://hostile.invalid")
	t.Setenv("GITHUB_TOKEN", "must-not-leak")
	t.Setenv("CHROME_BIN", "/tmp/host-browser")
	t.Setenv("CHROME_DEVEL_SANDBOX", "/tmp/host-sandbox")
	t.Setenv("HOME", "/tmp/host-home")

	want := literalRendererEnvironment(true)
	got := vhsExecEnvironment()
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("VHS exec environment = %#v, want exact ordered allowlist %#v", got, want)
	}
	assertEnvironmentExcludesHostState(t, got)
}

func TestCaptureUsesDistinctHelperAndExecEnvironments(t *testing.T) {
	helper := captureHelperEnvironment()
	execEnvironment := vhsExecEnvironment()
	if reflect.DeepEqual(helper, execEnvironment) {
		t.Fatal("capture helper and VHS exec environments are the same conflated vector")
	}
	if got := strings.Count(strings.Join(helper, "\n"), "VHS_NO_SANDBOX="); got != 0 {
		t.Fatalf("capture helper VHS_NO_SANDBOX count = %d, want 0", got)
	}
	if got := strings.Count(strings.Join(execEnvironment, "\n"), "VHS_NO_SANDBOX=1"); got != 1 {
		t.Fatalf("VHS exec exception count = %d, want 1", got)
	}
	if execEnvironment[23] != "VHS_NO_SANDBOX=1" || execEnvironment[22] != "SOURCE_DATE_EPOCH=946684800" {
		t.Fatalf("VHS exception placement = %#v, want immediately after SOURCE_DATE_EPOCH", execEnvironment)
	}
}

func literalRendererEnvironment(includeVHSException bool) []string {
	environment := []string{
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
	}
	if includeVHSException {
		environment = append(environment, "VHS_NO_SANDBOX=1")
	}
	return append(environment,
		"FONTCONFIG_FILE=/etc/fonts/fonts.conf",
		"FONTCONFIG_PATH=/etc/fonts",
		"EZA_CONFIG_DIR=/work/eza-config",
		"EZA_COLORS=",
		"LS_COLORS=",
	)
}

func assertEnvironmentExcludesHostState(t *testing.T, environment []string) {
	t.Helper()
	joined := strings.Join(environment, "\n")
	for _, forbidden := range []string{
		"http://hostile.invalid",
		"must-not-leak",
		"/tmp/host-browser",
		"/tmp/host-sandbox",
		"/tmp/host-home",
		"HTTPS_PROXY=",
		"GITHUB_TOKEN=",
		"CHROME_BIN=",
		"CHROME_DEVEL_SANDBOX=",
	} {
		if strings.Contains(joined, forbidden) {
			t.Fatalf("environment contains forbidden host state %q: %#v", forbidden, environment)
		}
	}
}

func TestPrepareRuntimeDirectoriesCreatesExactPrivateState(t *testing.T) {
	root := filepath.Join(t.TempDir(), "work")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatalf("create runtime root: %v", err)
	}

	if err := prepareRuntimeDirectoriesAt(root); err != nil {
		t.Fatalf("prepareRuntimeDirectoriesAt() error = %v", err)
	}

	wantDirectories := []string{
		"cache",
		"config",
		"data",
		"demo",
		"eza-config",
		"home",
		"runtime",
		"tmp",
		"zdotdir",
	}
	entries, err := os.ReadDir(root)
	if err != nil {
		t.Fatalf("read runtime root: %v", err)
	}
	gotDirectories := make([]string, 0, len(entries))
	for _, entry := range entries {
		if !entry.IsDir() {
			t.Fatalf("runtime root entry %q is not a directory", entry.Name())
		}
		gotDirectories = append(gotDirectories, entry.Name())
	}
	if !reflect.DeepEqual(gotDirectories, wantDirectories) {
		t.Fatalf("runtime directories = %#v, want %#v", gotDirectories, wantDirectories)
	}

	for _, name := range wantDirectories {
		assertOwnedMode(t, filepath.Join(root, name), 0o700)
	}

	const wantZshrc = "PROMPT='demo > '\nRPROMPT=''\nPROMPT_EOL_MARK=''\nunsetopt promptsubst\nsetopt no_beep\n"
	zshrc := filepath.Join(root, "zdotdir", ".zshrc")
	content, err := os.ReadFile(zshrc)
	if err != nil {
		t.Fatalf("read fixed zsh startup: %v", err)
	}
	if got := string(content); got != wantZshrc {
		t.Fatalf("fixed zsh startup = %q, want %q", got, wantZshrc)
	}
	assertOwnedMode(t, zshrc, 0o600)

	ezaEntries, err := os.ReadDir(filepath.Join(root, "eza-config"))
	if err != nil {
		t.Fatalf("read eza config directory: %v", err)
	}
	if len(ezaEntries) != 0 {
		t.Fatalf("eza config directory contains %d entries, want empty", len(ezaEntries))
	}
}

func TestPrepareRuntimeDirectoriesRejectsUnsafeExistingState(t *testing.T) {
	tests := []struct {
		name   string
		poison func(*testing.T, string) string
	}{
		{
			name: "runtime-root-symlink",
			poison: func(t *testing.T, root string) string {
				if err := os.Remove(root); err != nil {
					t.Fatalf("remove runtime root: %v", err)
				}
				outside := filepath.Join(t.TempDir(), "outside")
				if err := os.Mkdir(outside, 0o700); err != nil {
					t.Fatalf("create outside directory: %v", err)
				}
				if err := os.Symlink(outside, root); err != nil {
					t.Fatalf("symlink runtime root: %v", err)
				}
				return ""
			},
		},
		{
			name: "private-directory-symlink",
			poison: func(t *testing.T, root string) string {
				outside := filepath.Join(t.TempDir(), "outside")
				if err := os.Mkdir(outside, 0o700); err != nil {
					t.Fatalf("create outside directory: %v", err)
				}
				if err := os.Symlink(outside, filepath.Join(root, "home")); err != nil {
					t.Fatalf("symlink private directory: %v", err)
				}
				return ""
			},
		},
		{
			name: "fixed-startup-symlink",
			poison: func(t *testing.T, root string) string {
				zdotdir := filepath.Join(root, "zdotdir")
				if err := os.Mkdir(zdotdir, 0o700); err != nil {
					t.Fatalf("create zdotdir: %v", err)
				}
				outside := filepath.Join(t.TempDir(), "outside-zshrc")
				if err := os.WriteFile(outside, []byte("sentinel\n"), 0o600); err != nil {
					t.Fatalf("write outside startup: %v", err)
				}
				if err := os.Symlink(outside, filepath.Join(zdotdir, ".zshrc")); err != nil {
					t.Fatalf("symlink startup: %v", err)
				}
				return outside
			},
		},
		{
			name: "fixed-startup-hardlink",
			poison: func(t *testing.T, root string) string {
				zdotdir := filepath.Join(root, "zdotdir")
				if err := os.Mkdir(zdotdir, 0o700); err != nil {
					t.Fatalf("create zdotdir: %v", err)
				}
				outside := filepath.Join(root, "outside-zshrc")
				if err := os.WriteFile(outside, []byte("sentinel\n"), 0o600); err != nil {
					t.Fatalf("write outside startup: %v", err)
				}
				if err := os.Link(outside, filepath.Join(zdotdir, ".zshrc")); err != nil {
					t.Fatalf("hardlink startup: %v", err)
				}
				return outside
			},
		},
		{
			name: "non-empty-eza-config",
			poison: func(t *testing.T, root string) string {
				eza := filepath.Join(root, "eza-config")
				if err := os.Mkdir(eza, 0o700); err != nil {
					t.Fatalf("create eza config: %v", err)
				}
				if err := os.WriteFile(filepath.Join(eza, "theme.yml"), []byte("poison\n"), 0o600); err != nil {
					t.Fatalf("write eza config: %v", err)
				}
				return ""
			},
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			root := filepath.Join(t.TempDir(), "work")
			if err := os.Mkdir(root, 0o700); err != nil {
				t.Fatalf("create runtime root: %v", err)
			}
			outside := test.poison(t, root)

			if err := prepareRuntimeDirectoriesAt(root); err == nil {
				t.Fatal("prepareRuntimeDirectoriesAt() error = nil, want unsafe-state rejection")
			}
			if outside != "" {
				content, err := os.ReadFile(outside)
				if err != nil {
					t.Fatalf("read outside sentinel: %v", err)
				}
				if got := string(content); got != "sentinel\n" {
					t.Fatalf("outside sentinel = %q, want unchanged", got)
				}
			}
		})
	}
}

func TestPrepareRuntimeDirectoriesNormalizesPrivateModes(t *testing.T) {
	root := filepath.Join(t.TempDir(), "work")
	if err := os.Mkdir(root, 0o700); err != nil {
		t.Fatalf("create runtime root: %v", err)
	}
	if err := prepareRuntimeDirectoriesAt(root); err != nil {
		t.Fatalf("initial runtime preparation: %v", err)
	}
	if err := os.Chmod(filepath.Join(root, "home"), 0o755); err != nil {
		t.Fatalf("poison home mode: %v", err)
	}
	if err := os.Chmod(filepath.Join(root, "zdotdir", ".zshrc"), 0o666); err != nil {
		t.Fatalf("poison startup mode: %v", err)
	}

	if err := prepareRuntimeDirectoriesAt(root); err != nil {
		t.Fatalf("repeat runtime preparation: %v", err)
	}
	assertOwnedMode(t, filepath.Join(root, "home"), 0o700)
	assertOwnedMode(t, filepath.Join(root, "zdotdir", ".zshrc"), 0o600)
}

func TestCapturePreparesAndEntersDemoBeforeRestrictedExec(t *testing.T) {
	t.Setenv("README_TERMINAL_DEMO_TEST_VHS", "/hostile/environment/vhs")

	var events []string
	err := captureWith("/trusted/readme.tape", captureDependencies{
		browserPreflight: func() error {
			events = append(events, "browser")
			return nil
		},
		prepareRuntime: func() error {
			events = append(events, "prepare")
			return nil
		},
		changeDirectory: func(path string) error {
			if path != "/work/demo" {
				t.Fatalf("capture working directory = %q, want /work/demo", path)
			}
			events = append(events, "chdir")
			return nil
		},
		vhsPath: "/trusted/vhs",
		execRestricted: func(spec sandbox.ExecSpec) error {
			events = append(events, "exec")
			if spec.Path != "/trusted/vhs" {
				t.Fatalf("restricted executable = %q, want trusted dependency path", spec.Path)
			}
			if want := []string{"/trusted/vhs", "/trusted/readme.tape"}; !reflect.DeepEqual(spec.Args, want) {
				t.Fatalf("restricted argv = %#v, want %#v", spec.Args, want)
			}
			return nil
		},
	})
	if err != nil {
		t.Fatalf("captureWith() error = %v", err)
	}
	if want := []string{"browser", "prepare", "chdir", "exec"}; !reflect.DeepEqual(events, want) {
		t.Fatalf("capture events = %#v, want %#v", events, want)
	}
}

func TestCaptureFailsClosedWithoutLandlockV3(t *testing.T) {
	if os.Getenv(testUnsupportedLandlockCapture) == "child" {
		err := captureWith(os.Getenv("README_TERMINAL_DEMO_TEST_TAPE"), captureDependencies{
			browserPreflight: func() error { return nil },
			prepareRuntime:   func() error { return nil },
			changeDirectory:  func(string) error { return nil },
			vhsPath:          os.Getenv("README_TERMINAL_DEMO_TEST_CAPTURE_VHS"),
			execRestricted: func(sandbox.ExecSpec) error {
				return sandbox.ErrLandlockV3Unavailable
			},
		})
		if err == nil {
			os.Exit(0)
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(failure.ExitCode(err))
	}

	directory := t.TempDir()
	marker := filepath.Join(directory, "vhs-started")
	fakeVHS := filepath.Join(directory, "vhs")
	script := "#!/bin/sh\nprintf started > '" + strings.ReplaceAll(marker, "'", "'\\''") + "'\n"
	if err := os.WriteFile(fakeVHS, []byte(script), 0o755); err != nil {
		t.Fatalf("write VHS launch sentinel: %v", err)
	}
	tape := filepath.Join(directory, "smoke.tape")
	if err := os.WriteFile(tape, []byte("Output /tmp/never.gif\n"), 0o600); err != nil {
		t.Fatalf("write smoke tape: %v", err)
	}

	command := exec.Command(os.Args[0], "-test.run=^TestCaptureFailsClosedWithoutLandlockV3$")
	command.Env = append(os.Environ(),
		testUnsupportedLandlockCapture+"=child",
		"README_TERMINAL_DEMO_TEST_CAPTURE_VHS="+fakeVHS,
		"README_TERMINAL_DEMO_TEST_TAPE="+tape,
	)
	output, err := command.CombinedOutput()
	var exitError *exec.ExitError
	if !errors.As(err, &exitError) {
		t.Fatalf("unsupported-ABI capture error = %v, want exit 4; output=%q", err, output)
	}
	if got := exitError.ExitCode(); got != 4 {
		t.Fatalf("unsupported-ABI capture exit = %d, want 4; output=%q", got, output)
	}
	if _, err := os.Stat(marker); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("VHS launch marker stat error = %v, want not-exist", err)
	}
	if got := string(output); !strings.Contains(got, "renderer-unavailable: runtime (runtime.unavailable)") {
		t.Fatalf("sanitized unsupported-ABI output = %q", got)
	}
	if strings.Contains(string(output), directory) {
		t.Fatalf("unsupported-ABI output leaked a host path: %q", output)
	}
}

func TestCapturePreflightFailuresMapRendererUnavailable(t *testing.T) {
	tests := []struct {
		name string
		err  error
	}{
		{name: "executable-path-validation", err: fmt.Errorf("%w: executable /secret/path", sandbox.ErrRestrictedExec)},
		{name: "embedded-NUL-argv", err: fmt.Errorf("%w: argv at /secret/path", sandbox.ErrRestrictedExec)},
		{name: "embedded-NUL-environment", err: fmt.Errorf("%w: environment at /secret/path", sandbox.ErrRestrictedExec)},
		{name: "duplicate-environment", err: fmt.Errorf("%w: duplicate environment at /secret/path", sandbox.ErrRestrictedExec)},
		{name: "policy-validation", err: fmt.Errorf("%w: policy at /secret/path", sandbox.ErrLandlockV3Unavailable)},
		{name: "ABI-2", err: fmt.Errorf("%w: ABI 2", sandbox.ErrLandlockV3Unavailable)},
		{name: "create-ruleset", err: fmt.Errorf("%w: create ruleset", sandbox.ErrLandlockV3Unavailable)},
		{name: "open-path", err: fmt.Errorf("%w: open /secret/path", sandbox.ErrLandlockV3Unavailable)},
		{name: "opened-FD-fstat", err: fmt.Errorf("%w: fstat /secret/path", sandbox.ErrLandlockV3Unavailable)},
		{name: "add-rule", err: fmt.Errorf("%w: add /secret/path", sandbox.ErrLandlockV3Unavailable)},
		{name: "vector-construction", err: fmt.Errorf("%w: vector /secret/path", sandbox.ErrRestrictedExec)},
		{name: "set-CLOEXEC", err: fmt.Errorf("%w: set CLOEXEC", sandbox.ErrLandlockV3Unavailable)},
		{name: "read-CLOEXEC", err: fmt.Errorf("%w: read CLOEXEC", sandbox.ErrLandlockV3Unavailable)},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			directory := t.TempDir()
			marker := filepath.Join(directory, "vhs-started")
			fakeVHS := filepath.Join(directory, "vhs")
			script := "#!/bin/sh\nprintf started > '" + strings.ReplaceAll(marker, "'", "'\\''") + "'\n"
			if err := os.WriteFile(fakeVHS, []byte(script), 0o755); err != nil {
				t.Fatalf("write VHS sentinel: %v", err)
			}

			rawExecReached := false
			err := captureWith("/secret/host/readme.tape", captureDependencies{
				browserPreflight: func() error { return nil },
				prepareRuntime:   func() error { return nil },
				changeDirectory:  func(string) error { return nil },
				vhsPath:          fakeVHS,
				execRestricted: func(sandbox.ExecSpec) error {
					if test.err == nil {
						rawExecReached = true
					}
					return test.err
				},
			})
			if rawExecReached {
				t.Fatal("raw exec sentinel was reached after preflight failure")
			}
			if _, statErr := os.Stat(marker); !errors.Is(statErr, os.ErrNotExist) {
				t.Fatalf("VHS sentinel stat error = %v, want not-exist", statErr)
			}
			if got := failure.Classify(err); got != failure.RendererUnavailable {
				t.Fatalf("failure class = %q, want %q; error=%q", got, failure.RendererUnavailable, err)
			}
			if got := failure.ExitCode(err); got != 4 {
				t.Fatalf("outer exit = %d, want normal exit 4; error=%q", got, err)
			}
			if got, want := err.Error(), "renderer-unavailable: runtime (runtime.unavailable)"; got != want {
				t.Fatalf("sanitized error = %q, want %q", got, want)
			}
			if strings.Contains(err.Error(), "/secret/") {
				t.Fatalf("sanitized output leaked raw detail: %q", err)
			}
		})
	}
}

func assertOwnedMode(t *testing.T, path string, want os.FileMode) {
	t.Helper()

	var stat unix.Stat_t
	if err := unix.Fstatat(unix.AT_FDCWD, path, &stat, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		t.Fatalf("inspect %s without following links: %v", path, err)
	}
	if got := os.FileMode(stat.Mode & 0o7777); got != want {
		t.Fatalf("mode for %s = %#o, want %#o", path, got, want)
	}
	if got, wantUID := int(stat.Uid), os.Geteuid(); got != wantUID {
		t.Fatalf("owner for %s = %d, want runtime UID %d", path, got, wantUID)
	}
	if got, wantGID := int(stat.Gid), os.Getegid(); got != wantGID {
		t.Fatalf("group for %s = %d, want runtime GID %d", path, got, wantGID)
	}
}

func TestRodLinuxBrowserCandidatesThroughChromiumMatchPinnedOrder(t *testing.T) {
	if chromiumLauncherPath != "/usr/bin/chromium" {
		t.Fatalf("Chromium launcher path = %q, want /usr/bin/chromium", chromiumLauncherPath)
	}
	if chromiumLauncherSHA256 != "2c8d32d29dc6781c35ae196ea83299d507ac88fc339301abe74672feda299779" {
		t.Fatalf("Chromium launcher SHA-256 = %q, want approved literal", chromiumLauncherSHA256)
	}
	want := []string{
		"chrome",
		"google-chrome",
		"/usr/bin/google-chrome",
		"microsoft-edge",
		"/usr/bin/microsoft-edge",
		"chromium",
	}
	if !reflect.DeepEqual(rodLinuxBrowserCandidatesThroughChromium, want) {
		t.Fatalf("Rod Linux candidates through Chromium = %#v, want %#v", rodLinuxBrowserCandidatesThroughChromium, want)
	}
}

func TestBrowserPreflightRejectsEveryEarlierRodCandidateInOrder(t *testing.T) {
	target, digest := writeLauncher(t, []byte("pinned chromium launcher\n"), 0o755)

	for shadowIndex, shadowCandidate := range rodLinuxBrowserCandidatesThroughChromium[:len(rodLinuxBrowserCandidatesThroughChromium)-1] {
		t.Run(shadowCandidate, func(t *testing.T) {
			var calls []string
			lookPath := func(candidate string) (string, error) {
				calls = append(calls, candidate)
				if candidate == shadowCandidate {
					return "/shadow/browser", nil
				}
				if candidate == "chromium" {
					return target, nil
				}
				return "", exec.ErrNotFound
			}

			err := validateBrowser(browserPreflightConfig{
				target:         target,
				expectedSHA256: digest,
				lookPath:       lookPath,
			})
			if err == nil {
				t.Fatal("validateBrowser() error = nil, want earlier-candidate rejection")
			}
			wantCalls := rodLinuxBrowserCandidatesThroughChromium[:shadowIndex+1]
			if !reflect.DeepEqual(calls, wantCalls) {
				t.Fatalf("candidate checks = %#v, want exact prefix %#v", calls, wantCalls)
			}
		})
	}
}

func TestBrowserPreflightValidatesPinnedLauncherWithoutFollowingLinks(t *testing.T) {
	good := []byte("pinned chromium launcher\n")
	goodDigest := sha256Hex(good)

	tests := []struct {
		name    string
		prepare func(*testing.T) string
		wantErr bool
	}{
		{
			name: "valid",
			prepare: func(t *testing.T) string {
				path, _ := writeLauncher(t, good, 0o755)
				return path
			},
		},
		{
			name: "missing",
			prepare: func(t *testing.T) string {
				return filepath.Join(t.TempDir(), "chromium")
			},
			wantErr: true,
		},
		{
			name: "symlink",
			prepare: func(t *testing.T) string {
				directory := t.TempDir()
				real := filepath.Join(directory, "real-chromium")
				if err := os.WriteFile(real, good, 0o755); err != nil {
					t.Fatalf("write real launcher: %v", err)
				}
				link := filepath.Join(directory, "chromium")
				if err := os.Symlink(real, link); err != nil {
					t.Fatalf("symlink launcher: %v", err)
				}
				return link
			},
			wantErr: true,
		},
		{
			name: "non-regular",
			prepare: func(t *testing.T) string {
				path := filepath.Join(t.TempDir(), "chromium")
				if err := os.Mkdir(path, 0o755); err != nil {
					t.Fatalf("make launcher directory: %v", err)
				}
				return path
			},
			wantErr: true,
		},
		{
			name: "wrong-mode",
			prepare: func(t *testing.T) string {
				path, _ := writeLauncher(t, good, 0o775)
				return path
			},
			wantErr: true,
		},
		{
			name: "wrong-owner",
			prepare: func(t *testing.T) string {
				path, _ := writeLauncher(t, good, 0o755)
				if err := unix.Chown(path, 65532, 65532); err != nil {
					t.Fatalf("change launcher owner: %v", err)
				}
				return path
			},
			wantErr: true,
		},
		{
			name: "one-byte-mutation",
			prepare: func(t *testing.T) string {
				mutated := append([]byte(nil), good...)
				mutated[0] ^= 1
				path, _ := writeLauncher(t, mutated, 0o755)
				return path
			},
			wantErr: true,
		},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			target := test.prepare(t)
			lookPath := func(candidate string) (string, error) {
				if candidate == "chromium" {
					return target, nil
				}
				return "", exec.ErrNotFound
			}
			err := validateBrowser(browserPreflightConfig{
				target:         target,
				expectedSHA256: goodDigest,
				lookPath:       lookPath,
			})
			if (err != nil) != test.wantErr {
				t.Fatalf("validateBrowser() error = %v, wantErr %t", err, test.wantErr)
			}
		})
	}
}

func TestCaptureMapsBrowserPreflightFailureBeforeLaunch(t *testing.T) {
	launched := false
	err := captureWith("/secret/host/path/readme.tape", captureDependencies{
		browserPreflight: func() error {
			return errors.New("browser failure at /secret/host/path")
		},
		prepareRuntime:  func() error { return nil },
		changeDirectory: func(string) error { return nil },
		vhsPath:         "/trusted/vhs",
		execRestricted: func(sandbox.ExecSpec) error {
			launched = true
			return errors.New("VHS or downloader sentinel ran")
		},
	})
	if launched {
		t.Fatal("VHS/downloader launch sentinel ran after failed browser preflight")
	}
	if got := failure.Classify(err); got != failure.RendererUnavailable {
		t.Fatalf("failure class = %q, want %q", got, failure.RendererUnavailable)
	}
	if got, want := err.Error(), "renderer-unavailable: runtime (runtime.unavailable)"; got != want {
		t.Fatalf("sanitized error = %q, want %q", got, want)
	}
	if strings.Contains(err.Error(), "/secret/") {
		t.Fatalf("sanitized error leaked internal path: %q", err)
	}
}

func TestBrowserBuildContractPinsLauncherAndForbidsGlobalSandboxOverrides(t *testing.T) {
	root := filepath.Clean(filepath.Join("..", ".."))
	dependencies, err := os.ReadFile(filepath.Join(root, "dependencies.env"))
	if err != nil {
		t.Fatalf("read dependencies.env: %v", err)
	}
	dockerfile, err := os.ReadFile(filepath.Join(root, "Dockerfile"))
	if err != nil {
		t.Fatalf("read Dockerfile: %v", err)
	}

	const launcherPin = "CHROMIUM_LAUNCHER_SHA256=2c8d32d29dc6781c35ae196ea83299d507ac88fc339301abe74672feda299779"
	if got := strings.Count(string(dependencies), launcherPin); got != 1 {
		t.Fatalf("dependencies.env launcher pin count = %d, want 1", got)
	}

	docker := string(dockerfile)
	for _, forbidden := range []string{
		"\"chromium-sandbox=",
		"ENV VHS_NO_SANDBOX=",
		"ENV CHROME_BIN=",
		"VHS_NO_SANDBOX=1",
		"CHROME_BIN=/usr/bin/chromium",
	} {
		if strings.Contains(docker, forbidden) {
			t.Fatalf("Dockerfile contains forbidden browser sandbox setting %q", forbidden)
		}
	}
	for _, required := range []string{
		"dpkg-query -W -f='${db:Status-Abbrev}' chromium-sandbox",
		"-name chrome-sandbox",
		"-name chromium-sandbox",
		"-perm /4000",
		"${CHROMIUM_LAUNCHER_SHA256}",
		"/usr/bin/chromium",
	} {
		if !strings.Contains(docker, required) {
			t.Fatalf("Dockerfile missing browser build assertion %q", required)
		}
	}

	const vhsExitStatusContract = `FROM runtime AS test
RUN set -eu; \
    test "$(/usr/local/bin/vhs --version)" = 'vhs version v0.11.0 (c6af91a)'; \
    vhs_status=0; \
    /usr/local/bin/vhs --definitely-invalid >/tmp/vhs-invalid.out 2>&1 || vhs_status=$?; \
    test "$vhs_status" -eq 1; \
    rm -f /tmp/vhs-invalid.out; \
    printf '%s\n' 'PASS TestPinnedVHSExitStatusContract'`
	if got := strings.Count(docker, vhsExitStatusContract); got != 1 {
		t.Fatalf("Dockerfile final runtime test-stage VHS exit-status contract count = %d, want exact block once", got)
	}
	testStage := strings.Index(docker, "FROM runtime AS test")
	if testStage < 0 {
		t.Fatal("Dockerfile is missing the final runtime test stage")
	}
	if strings.Contains(docker[:testStage], "TestPinnedVHSExitStatusContract") {
		t.Fatal("VHS exit-status contract appears before the final runtime test stage")
	}
}

func writeLauncher(t *testing.T, content []byte, mode os.FileMode) (string, string) {
	t.Helper()

	path := filepath.Join(t.TempDir(), "chromium")
	if err := os.WriteFile(path, content, mode); err != nil {
		t.Fatalf("write launcher: %v", err)
	}
	if err := os.Chmod(path, mode); err != nil {
		t.Fatalf("set launcher mode: %v", err)
	}
	return path, sha256Hex(content)
}

func sha256Hex(content []byte) string {
	digest := sha256.Sum256(content)
	return fmt.Sprintf("%x", digest[:])
}
