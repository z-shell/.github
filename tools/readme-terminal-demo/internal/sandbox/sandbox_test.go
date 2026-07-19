package sandbox_test

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"testing"
	"time"

	llsyscall "github.com/landlock-lsm/go-landlock/landlock/syscall"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/sandbox"
	"golang.org/x/sys/unix"
)

const (
	rawDeviceBoundaryMode   = "README_TERMINAL_DEMO_TEST_RAW_DEVICE_BOUNDARY"
	escapedPipeHolderMode   = "README_TERMINAL_DEMO_TEST_ESCAPED_PIPE_HOLDER"
	escapedPipeHolderPID    = "README_TERMINAL_DEMO_TEST_ESCAPED_PIPE_PID"
	escapedPipeHolderMarker = "README_TERMINAL_DEMO_TEST_ESCAPED_PIPE_MARKER"
)

func TestRunRestrictedChildCleansGroupAfterEveryOutcome(t *testing.T) {
	const childScript = `
ulimit -c 0
printf '%s\n' "$$" > "$1"
(
  IFS=' ' read -r descendant_pid _ < /proc/self/stat
  printf '%s\n' "$descendant_pid" > "$3"
  while [ ! -e "$4" ]; do sleep 0.01; done
  printf staged > "$2"
) &
while [ ! -s "$3" ]; do sleep 0.01; done
case "$5" in
  exit-0) exit 0 ;;
  exit-1) exit 1 ;;
  exit-4) exit 4 ;;
  exit-5) exit 5 ;;
  signal-4) kill -4 "$$" ;;
  signal-5) kill -5 "$$" ;;
  timeout) sleep 60 ;;
esac
exit 99
`
	tests := []struct {
		name    string
		mode    string
		timeout time.Duration
		want    sandbox.Outcome
		wantErr error
	}{
		{name: "normal-exit-zero", mode: "exit-0", want: sandbox.Outcome{Exited: true, ExitCode: 0}},
		{name: "normal-exit-one", mode: "exit-1", want: sandbox.Outcome{Exited: true, ExitCode: 1}},
		{name: "normal-exit-four", mode: "exit-4", want: sandbox.Outcome{Exited: true, ExitCode: 4}},
		{name: "normal-exit-five", mode: "exit-5", want: sandbox.Outcome{Exited: true, ExitCode: 5}},
		{name: "signal-four", mode: "signal-4", want: sandbox.Outcome{Signaled: true, Signal: unix.Signal(4)}},
		{name: "signal-five", mode: "signal-5", want: sandbox.Outcome{Signaled: true, Signal: unix.Signal(5)}},
		{name: "timeout", mode: "timeout", timeout: 100 * time.Millisecond, want: sandbox.Outcome{TimedOut: true}, wantErr: sandbox.ErrProcessTimeout},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			directory := t.TempDir()
			pidPath := filepath.Join(directory, "direct.pid")
			stagingPath := filepath.Join(directory, "staging-byte")
			descendantPIDPath := filepath.Join(directory, "descendant.pid")
			gatePath := filepath.Join(directory, "descendant.gate")
			timeout := test.timeout
			if timeout == 0 {
				timeout = 2 * time.Second
			}
			outcome, err := sandbox.RunRestrictedChild(context.Background(), sandbox.Child{
				Path:    "/bin/sh",
				Args:    []string{"-c", childScript, "sh", pidPath, stagingPath, descendantPIDPath, gatePath, test.mode},
				Timeout: timeout,
			})
			if test.wantErr == nil {
				if err != nil {
					t.Fatalf("RunRestrictedChild() error = %v, want nil", err)
				}
			} else if !errors.Is(err, test.wantErr) {
				t.Fatalf("RunRestrictedChild() error = %v, want %v", err, test.wantErr)
			}
			if outcome != test.want {
				t.Fatalf("RunRestrictedChild() outcome = %#v, want %#v", outcome, test.want)
			}

			pid := readProcessID(t, pidPath, time.Second)
			if err := unix.Kill(pid, 0); !errors.Is(err, unix.ESRCH) {
				t.Fatalf("direct child PID %d remains after wait/reap: %v", pid, err)
			}
			descendantPID := readProcessID(t, descendantPIDPath, time.Second)
			t.Cleanup(func() {
				_ = os.WriteFile(gatePath, []byte("release"), 0o600)
				_ = unix.Kill(descendantPID, unix.SIGKILL)
			})
			if err := waitForProcessTermination(descendantPID, time.Second); err != nil {
				t.Fatalf("descendant cleanup: %v", err)
			}
			if err := os.WriteFile(gatePath, []byte("release"), 0o600); err != nil {
				t.Fatalf("release descendant gate: %v", err)
			}
			time.Sleep(100 * time.Millisecond)
			if _, err := os.Stat(stagingPath); !errors.Is(err, os.ErrNotExist) {
				t.Fatalf("descendant survived group cleanup and crossed its gate: %v", err)
			}
		})
	}
}

func waitForProcessTermination(pid int, timeout time.Duration) error {
	deadline := time.Now().Add(timeout)
	for {
		err := unix.Kill(pid, 0)
		if errors.Is(err, unix.ESRCH) {
			return nil
		}
		if err != nil {
			return fmt.Errorf("inspect PID %d: %w", pid, err)
		}
		stat, readErr := os.ReadFile(fmt.Sprintf("/proc/%d/stat", pid))
		if errors.Is(readErr, os.ErrNotExist) {
			return nil
		}
		if readErr != nil {
			return fmt.Errorf("read PID %d state: %w", pid, readErr)
		}
		stateStart := strings.LastIndex(string(stat), ") ")
		if stateStart < 0 {
			return fmt.Errorf("parse PID %d state %q", pid, stat)
		}
		fields := strings.Fields(string(stat[stateStart+2:]))
		if len(fields) == 0 {
			return fmt.Errorf("parse PID %d state %q", pid, stat)
		}
		if fields[0] == "Z" {
			return nil
		}
		if time.Now().After(deadline) {
			return fmt.Errorf("PID %d remains live in state %q after group cleanup", pid, fields[0])
		}
		time.Sleep(10 * time.Millisecond)
	}
}

func TestRunRestrictedChildBoundsEscapedPipeHolder(t *testing.T) {
	if os.Getenv(escapedPipeHolderMode) == "holder" {
		if _, err := unix.Setsid(); err != nil {
			_, _ = fmt.Fprintf(os.Stderr, "setsid: %v\n", err)
			os.Exit(20)
		}
		if err := os.WriteFile(os.Getenv(escapedPipeHolderPID), []byte(strconv.Itoa(os.Getpid())), 0o600); err != nil {
			_, _ = fmt.Fprintf(os.Stderr, "write escaped PID: %v\n", err)
			os.Exit(21)
		}
		time.Sleep(4 * time.Second)
		if err := os.WriteFile(os.Getenv(escapedPipeHolderMarker), []byte("staged"), 0o600); err != nil {
			_, _ = fmt.Fprintf(os.Stderr, "write escaped marker: %v\n", err)
			os.Exit(22)
		}
		time.Sleep(time.Minute)
		os.Exit(0)
	}

	directory := t.TempDir()
	pidPath := filepath.Join(directory, "escaped.pid")
	stagingPath := filepath.Join(directory, "escaped-staging-byte")
	const launcherScript = `
"$1" -test.run='^TestRunRestrictedChildBoundsEscapedPipeHolder$' &
while [ ! -s "$2" ]; do sleep 0.01; done
exit 0
`
	var output bytes.Buffer
	type result struct {
		outcome sandbox.Outcome
		err     error
	}
	resultChannel := make(chan result, 1)
	started := time.Now()
	go func() {
		outcome, err := sandbox.RunRestrictedChild(context.Background(), sandbox.Child{
			Path: "/bin/sh",
			Args: []string{"-c", launcherScript, "sh", os.Args[0], pidPath},
			Env: []string{
				"PATH=/usr/bin:/bin",
				escapedPipeHolderMode + "=holder",
				escapedPipeHolderPID + "=" + pidPath,
				escapedPipeHolderMarker + "=" + stagingPath,
			},
			Stdout:  &output,
			Stderr:  &output,
			Timeout: 8 * time.Second,
		})
		resultChannel <- result{outcome: outcome, err: err}
	}()

	var got result
	select {
	case got = <-resultChannel:
	case <-time.After(5 * time.Second):
		pid := readProcessID(t, pidPath, time.Second)
		_ = unix.Kill(pid, unix.SIGKILL)
		select {
		case <-resultChannel:
		case <-time.After(2 * time.Second):
		}
		t.Fatal("RunRestrictedChild did not bound an escaped pipe holder")
	}

	escapedPID := readProcessID(t, pidPath, time.Second)
	defer unix.Kill(escapedPID, unix.SIGKILL)
	if got.outcome != (sandbox.Outcome{Exited: true, ExitCode: 0}) {
		t.Fatalf("escaped-holder outcome = %#v, want normal exit 0", got.outcome)
	}
	if !errors.Is(got.err, exec.ErrWaitDelay) {
		t.Fatalf("escaped-holder error = %v, want exec.ErrWaitDelay; output=%q", got.err, output.Bytes())
	}
	if elapsed := time.Since(started); elapsed < 1500*time.Millisecond || elapsed > 4*time.Second {
		t.Fatalf("escaped-holder bounded return took %s, want approximately two seconds", elapsed)
	}
	if _, err := os.Stat(stagingPath); !errors.Is(err, os.ErrNotExist) {
		t.Fatalf("escaped staging witness was read before bounded cleanup: %v", err)
	}
}

func readProcessID(t *testing.T, path string, timeout time.Duration) int {
	t.Helper()

	deadline := time.Now().Add(timeout)
	for {
		content, err := os.ReadFile(path)
		if err == nil {
			pid, conversionErr := strconv.Atoi(strings.TrimSpace(string(content)))
			if conversionErr != nil || pid <= 0 {
				t.Fatalf("parse process ID %q: %v", content, conversionErr)
			}
			return pid
		}
		if !errors.Is(err, os.ErrNotExist) || time.Now().After(deadline) {
			t.Fatalf("read process ID %s: %v", path, err)
		}
		time.Sleep(10 * time.Millisecond)
	}
}

func TestRawExecDeviceBoundary(t *testing.T) {
	switch os.Getenv(rawDeviceBoundaryMode) {
	case "target":
		if err := writeDevice("/dev/null"); err != nil {
			t.Fatal(err)
		}
		masterFD, err := unix.Open("/dev/pts/ptmx", unix.O_RDWR|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
		if err != nil {
			t.Fatalf("open PTY master after raw exec: %v", err)
		}
		defer unix.Close(masterFD)
		if err := unix.IoctlSetPointerInt(masterFD, unix.TIOCSPTLCK, 0); err != nil {
			t.Fatalf("unlock PTY after raw exec: %v", err)
		}
		ptyNumber, err := unix.IoctlGetInt(masterFD, unix.TIOCGPTN)
		if err != nil {
			t.Fatalf("read PTY number after raw exec: %v", err)
		}
		slavePath := "/dev/pts/" + strconv.Itoa(ptyNumber)
		slaveFD, err := unix.Open(slavePath, unix.O_RDWR|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
		if err != nil {
			t.Fatalf("open dynamic PTY slave after raw exec: %v", err)
		}
		var slaveStat unix.Stat_t
		if err := unix.Fstat(slaveFD, &slaveStat); err != nil {
			_ = unix.Close(slaveFD)
			t.Fatalf("inspect dynamic PTY slave: %v", err)
		}
		if slaveStat.Mode&unix.S_IFMT != unix.S_IFCHR {
			_ = unix.Close(slaveFD)
			t.Fatalf("dynamic PTY slave mode = %#o, want character device", slaveStat.Mode)
		}
		if err := unix.Close(slaveFD); err != nil {
			t.Fatalf("close dynamic PTY slave: %v", err)
		}
		fd, err := unix.Open("/dev/zero", unix.O_WRONLY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
		if err == nil {
			_ = unix.Close(fd)
			t.Fatal("/dev/zero remained writable after raw exec")
		}
		if !errors.Is(err, unix.EACCES) {
			t.Fatalf("open /dev/zero after raw exec: %v; want EACCES", err)
		}
		return
	case "launcher":
		if err := requireCharacterDevice("/dev/null", 1, 3); err != nil {
			t.Fatal(err)
		}
		if err := requireCharacterDevice("/dev/zero", 1, 5); err != nil {
			t.Fatal(err)
		}
		if err := requireCharacterDevice("/dev/pts/ptmx", 5, 2); err != nil {
			t.Fatal(err)
		}
		if err := writeDevice("/dev/zero"); err != nil {
			t.Fatal(err)
		}
		executable, err := os.Executable()
		if err != nil {
			t.Fatalf("resolve test executable: %v", err)
		}
		sandbox.ExecRestricted(sandbox.ExecSpec{
			Path: executable,
			Args: []string{executable, "-test.run=^TestRawExecDeviceBoundary$"},
			Env:  []string{rawDeviceBoundaryMode + "=target"},
			Policy: sandbox.Policy{
				ReadOnlyPaths: existingDirectories(
					"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(executable),
				),
				AllowPrivateDevptsPTY: true,
			},
		})
		t.Fatal("ExecRestricted returned after successful preflight")
	}

	abi, err := llsyscall.LandlockGetABIVersion()
	if err != nil {
		t.Skipf("detect live Landlock ABI: %v", err)
	}
	t.Logf("detected live Landlock ABI: %d", abi)
	if abi < 3 {
		t.Skipf("detected live Landlock ABI %d; raw device boundary requires ABI 3", abi)
	}

	command := exec.Command(os.Args[0], "-test.run=^TestRawExecDeviceBoundary$")
	command.Env = []string{rawDeviceBoundaryMode + "=launcher"}
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("raw-exec device-boundary helper: %v; output=%q", err, output)
	}
}

func existingDirectories(paths ...string) []string {
	result := make([]string, 0, len(paths))
	seen := make(map[string]struct{}, len(paths))
	for _, path := range paths {
		clean := filepath.Clean(path)
		if _, duplicate := seen[clean]; duplicate {
			continue
		}
		info, err := os.Stat(clean)
		if err == nil && info.IsDir() {
			seen[clean] = struct{}{}
			result = append(result, clean)
		}
	}
	return result
}

func requireCharacterDevice(path string, wantMajor, wantMinor uint32) error {
	var stat unix.Stat_t
	if err := unix.Fstatat(unix.AT_FDCWD, path, &stat, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fmt.Errorf("inspect %s without following links: %w", path, err)
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFCHR {
		return fmt.Errorf("%s is not a character device", path)
	}
	if major, minor := unix.Major(uint64(stat.Rdev)), unix.Minor(uint64(stat.Rdev)); major != wantMajor || minor != wantMinor {
		return fmt.Errorf("%s identity is %d:%d; want %d:%d", path, major, minor, wantMajor, wantMinor)
	}
	return nil
}

func writeDevice(path string) error {
	fd, err := unix.Open(path, unix.O_WRONLY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return fmt.Errorf("open %s for write: %w", path, err)
	}
	if _, err := unix.Write(fd, []byte{0}); err != nil {
		_ = unix.Close(fd)
		return fmt.Errorf("write %s: %w", path, err)
	}
	if err := unix.Close(fd); err != nil {
		return fmt.Errorf("close %s: %w", path, err)
	}
	return nil
}
