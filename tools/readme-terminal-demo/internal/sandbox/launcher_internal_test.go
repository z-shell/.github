package sandbox

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strconv"
	"strings"
	"testing"
	"time"
	"unsafe"

	llsyscall "github.com/landlock-lsm/go-landlock/landlock/syscall"
	"golang.org/x/sys/unix"
)

const (
	testExecProbeMode         = "README_TERMINAL_DEMO_TEST_EXEC_PROBE"
	testPreserveRulesetMode   = "README_TERMINAL_DEMO_TEST_PRESERVE_RULESET"
	testPreserveRulesetCase   = "README_TERMINAL_DEMO_TEST_PRESERVE_CASE"
	testCloseRangeUnshareMode = "README_TERMINAL_DEMO_TEST_CLOSE_RANGE_UNSHARE"
	testDecoyExecMode         = "README_TERMINAL_DEMO_TEST_DECOY_EXEC"
	testDecoyLowerPath        = "README_TERMINAL_DEMO_TEST_DECOY_LOWER_PATH"
	testDecoyUpperPath        = "README_TERMINAL_DEMO_TEST_DECOY_UPPER_PATH"
	testExecVectorMode        = "README_TERMINAL_DEMO_TEST_EXEC_VECTOR_GC"
	testStageExitGroupMode    = "README_TERMINAL_DEMO_TEST_STAGE_EXIT_GROUP"
	testStageExitGroupFault   = "README_TERMINAL_DEMO_TEST_STAGE_FAULT"
	testSuccessfulExecMode    = "README_TERMINAL_DEMO_TEST_SUCCESSFUL_EXEC_SIBLING"
)

const (
	testMovedRulesetFD = 100
	testLowerDecoyFD   = 50
	testUpperDecoyFD   = 150
)

func TestExecutePreparedFailureStagesExitGroup(t *testing.T) {
	if os.Getenv(testStageExitGroupMode) == "child" {
		faultName := os.Getenv(testStageExitGroupFault)
		fault, _ := requiredTerminalFault(t, faultName)
		preparedPtr := preparedExecForTerminalTest(t, "TestExecutePreparedFailureStagesExitGroup", nil)
		preparedPtr.fault = fault
		startLockedPausedSibling()
		executePrepared(preparedPtr)
	}

	tests := []struct {
		name     string
		wantExit int
	}{
		{name: "upper-close", wantExit: runtimeFailureExitCode},
		{name: "lower-close", wantExit: runtimeFailureExitCode},
		{name: "no-new-privs", wantExit: runtimeFailureExitCode},
		{name: "restrict-self", wantExit: runtimeFailureExitCode},
		{name: "ruleset-close", wantExit: runtimeFailureExitCode},
		{name: "tid-mismatch", wantExit: runtimeFailureExitCode},
		{name: "execve", wantExit: executionFailureExitCode},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
			defer cancel()
			command := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestExecutePreparedFailureStagesExitGroup$")
			command.Env = []string{
				testStageExitGroupMode + "=child",
				testStageExitGroupFault + "=" + test.name,
			}
			started := time.Now()
			output, err := command.CombinedOutput()
			if errors.Is(ctx.Err(), context.DeadlineExceeded) {
				t.Fatalf("stage %s left a sibling OS thread alive; output=%q", test.name, output)
			}
			assertExitCode(t, err, test.wantExit, output)
			if elapsed := time.Since(started); elapsed > time.Second {
				t.Fatalf("stage %s process-wide exit took %s", test.name, elapsed)
			}
		})
	}
}

func requiredTerminalFault(t *testing.T, name string) (terminalFault, int) {
	t.Helper()

	switch name {
	case "upper-close":
		return terminalFaultUpperClose, runtimeFailureExitCode
	case "lower-close":
		return terminalFaultLowerClose, runtimeFailureExitCode
	case "no-new-privs":
		return terminalFaultNoNewPrivs, runtimeFailureExitCode
	case "restrict-self":
		return terminalFaultRestrictSelf, runtimeFailureExitCode
	case "ruleset-close":
		return terminalFaultRulesetClose, runtimeFailureExitCode
	case "tid-mismatch":
		return terminalFaultTIDMismatch, runtimeFailureExitCode
	case "execve":
		return terminalFaultExecve, executionFailureExitCode
	default:
		t.Fatalf("unknown terminal fault stage %q", name)
		return terminalFaultNone, 0
	}
}

func TestSuccessfulExecDestroysSibling(t *testing.T) {
	switch os.Getenv(testSuccessfulExecMode) {
	case "target":
		return
	case "launcher":
		startLockedPausedSibling()
		if err := ExecRestricted(ExecSpec{
			Path: mustTestExecutable(t),
			Args: []string{mustTestExecutable(t), "-test.run=^TestSuccessfulExecDestroysSibling$"},
			Env:  []string{testSuccessfulExecMode + "=target"},
			Policy: Policy{ReadOnlyPaths: existingTestDirectories(
				"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(mustTestExecutable(t)),
			)},
		}); err != nil {
			t.Fatalf("ExecRestricted() error = %v", err)
		}
		t.Fatal("ExecRestricted returned after successful preflight")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestSuccessfulExecDestroysSibling$")
	command.Env = []string{testSuccessfulExecMode + "=launcher"}
	output, err := command.CombinedOutput()
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatalf("successful exec left the pre-exec sibling alive; output=%q", output)
	}
	if err != nil {
		t.Fatalf("successful raw-exec sibling helper: %v; output=%q", err, output)
	}
}

func preparedExecForTerminalTest(t *testing.T, testName string, environment []string) *preparedExec {
	t.Helper()

	executable := mustTestExecutable(t)
	preparedPtr, err := prepareRestrictedExec(ExecSpec{
		Path: executable,
		Args: []string{executable, "-test.run=^" + testName + "$"},
		Env:  environment,
		Policy: Policy{ReadOnlyPaths: existingTestDirectories(
			"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(executable),
		)},
	})
	if err != nil {
		t.Fatalf("prepare terminal-stage exec: %v", err)
	}
	return preparedPtr
}

func mustTestExecutable(t *testing.T) string {
	t.Helper()

	executable, err := os.Executable()
	if err != nil {
		t.Fatalf("resolve helper executable: %v", err)
	}
	return executable
}

func startLockedPausedSibling() {
	ready := make(chan struct{})
	go func() {
		runtime.LockOSThread()
		close(ready)
		for {
			_, _, _ = unix.RawSyscall(unix.SYS_PAUSE, 0, 0, 0)
		}
	}()
	<-ready
}

func TestExecRestrictedPreservesLandlockAcrossRawExec(t *testing.T) {
	mode := os.Getenv(testExecProbeMode)
	if mode == "target" {
		assertPostExecBoundary(t)
		return
	}
	if mode == "launcher" {
		executable, err := os.Executable()
		if err != nil {
			t.Fatalf("resolve helper executable: %v", err)
		}
		allowed := os.Getenv("README_TERMINAL_DEMO_TEST_ALLOWED")
		ExecRestricted(ExecSpec{
			Path: executable,
			Args: []string{executable, "-test.run=^TestExecRestrictedPreservesLandlockAcrossRawExec$"},
			Env: []string{
				testExecProbeMode + "=target",
				"README_TERMINAL_DEMO_TEST_ALLOWED=" + allowed,
				"README_TERMINAL_DEMO_TEST_DENIED_READ=" + os.Getenv("README_TERMINAL_DEMO_TEST_DENIED_READ"),
				"README_TERMINAL_DEMO_TEST_DENIED_WRITE=" + os.Getenv("README_TERMINAL_DEMO_TEST_DENIED_WRITE"),
			},
			Policy: Policy{ReadOnlyPaths: existingTestDirectories(
				"/usr", "/etc", "/proc", "/sys", "/dev",
				filepath.Dir(executable), filepath.Dir(allowed),
			)},
		})
		t.Fatal("ExecRestricted returned after successful preflight")
	}
	abi, err := llsyscall.LandlockGetABIVersion()
	if err != nil {
		t.Skipf("detect live Landlock ABI: %v", err)
	}
	t.Logf("detected live Landlock ABI: %d", abi)
	if abi < 3 {
		t.Skipf("detected live Landlock ABI %d; raw path boundary requires ABI 3", abi)
	}

	directory := t.TempDir()
	allowedDirectory := filepath.Join(directory, "allowed")
	deniedDirectory := filepath.Join(directory, "denied")
	if err := os.MkdirAll(allowedDirectory, 0o700); err != nil {
		t.Fatalf("create allowed directory: %v", err)
	}
	if err := os.MkdirAll(deniedDirectory, 0o700); err != nil {
		t.Fatalf("create denied directory: %v", err)
	}
	allowed := filepath.Join(allowedDirectory, "readable")
	deniedRead := filepath.Join(deniedDirectory, "readable")
	deniedWrite := filepath.Join(deniedDirectory, "write-probe")
	if err := os.WriteFile(allowed, []byte("allowed"), 0o600); err != nil {
		t.Fatalf("write allowed fixture: %v", err)
	}
	if err := os.WriteFile(deniedRead, []byte("denied"), 0o600); err != nil {
		t.Fatalf("write denied fixture: %v", err)
	}

	command := exec.Command(os.Args[0], "-test.run=^TestExecRestrictedPreservesLandlockAcrossRawExec$")
	command.Env = []string{
		testExecProbeMode + "=launcher",
		"README_TERMINAL_DEMO_TEST_ALLOWED=" + allowed,
		"README_TERMINAL_DEMO_TEST_DENIED_READ=" + deniedRead,
		"README_TERMINAL_DEMO_TEST_DENIED_WRITE=" + deniedWrite,
	}
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("post-exec Landlock helper: %v; output=%q", err, output)
	}
}

func assertPostExecBoundary(t *testing.T) {
	t.Helper()

	allowed := os.Getenv("README_TERMINAL_DEMO_TEST_ALLOWED")
	content, err := os.ReadFile(allowed)
	if err != nil || string(content) != "allowed" {
		t.Fatalf("allowed read after exec = %q, %v", content, err)
	}
	if _, err := os.ReadFile(os.Getenv("README_TERMINAL_DEMO_TEST_DENIED_READ")); !errors.Is(err, unix.EACCES) {
		t.Fatalf("denied read after exec error = %v, want EACCES", err)
	}
	deniedWrite := os.Getenv("README_TERMINAL_DEMO_TEST_DENIED_WRITE")
	file, err := os.OpenFile(deniedWrite, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0o600)
	if err == nil {
		_ = file.Close()
		t.Fatal("denied write after exec unexpectedly succeeded")
	}
	if !errors.Is(err, unix.EACCES) {
		t.Fatalf("denied write after exec error = %v, want EACCES", err)
	}
}

func existingTestDirectories(paths ...string) []string {
	result := make([]string, 0, len(paths))
	seen := make(map[string]struct{}, len(paths))
	for _, path := range paths {
		clean := filepath.Clean(path)
		if _, ok := seen[clean]; ok {
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

func assertExitCode(t *testing.T, err error, want int, output []byte) {
	t.Helper()

	var exitError *exec.ExitError
	if !errors.As(err, &exitError) {
		t.Fatalf("child error = %v, want exit %d; output=%q", err, want, output)
	}
	if got := exitError.ExitCode(); got != want {
		t.Fatalf("child exit = %d, want %d; output=%q", got, want, output)
	}
}

func TestSanitizedPostLockExitCodes(t *testing.T) {
	if runtimeFailureExitCode != 4 {
		t.Fatalf("runtime failure exit code = %s, want 4", strconv.Itoa(runtimeFailureExitCode))
	}
	if executionFailureExitCode != 5 {
		t.Fatalf("execution failure exit code = %s, want 5", strconv.Itoa(executionFailureExitCode))
	}
}

func TestPrepareV3RejectsABI2BeforeCreatingRuleset(t *testing.T) {
	fake := newPrepareV3Fake(2)

	_, err := prepareV3WithOps(Policy{
		ReadOnlyPaths:  []string{"/must-not-open-ro"},
		ReadWritePaths: []string{"/must-not-open-rw"},
	}, fake.ops())
	if !errors.Is(err, ErrLandlockV3Unavailable) {
		t.Fatalf("prepareV3WithOps() error = %v, want ErrLandlockV3Unavailable", err)
	}
	if !reflect.DeepEqual(fake.events, []string{"abi"}) {
		t.Fatalf("ABI 2 operations = %#v, want only ABI query", fake.events)
	}
	if len(fake.closed) != 0 {
		t.Fatalf("ABI 2 closed descriptors = %#v, want none owned", fake.closed)
	}
}

func TestPrepareV3BuildsExactABIV3Ruleset(t *testing.T) {
	for _, abi := range []int{3, 9} {
		t.Run("abi-"+strconv.Itoa(abi), func(t *testing.T) {
			fake := newPrepareV3Fake(abi)
			prepared, err := prepareV3WithOps(Policy{
				ReadOnlyPaths:         []string{"/z-ro", "/a-ro"},
				ReadWritePaths:        []string{"/z-rw", "/a-rw"},
				AllowPrivateDevptsPTY: true,
			}, fake.ops())
			if err != nil {
				t.Fatalf("prepareV3WithOps() error = %v", err)
			}
			if prepared.rulesetFD != fake.rulesetFD {
				t.Fatalf("prepared ruleset FD = %d, want %d", prepared.rulesetFD, fake.rulesetFD)
			}

			wantRuleset := llsyscall.RulesetAttr{
				HandledAccessFS:  exactV3HandledAccess,
				HandledAccessNet: 0,
				Scoped:           0,
			}
			if fake.createFlags != 0 || fake.rulesetAttr != wantRuleset {
				t.Fatalf("create ruleset = %#v flags=%d, want %#v flags=0", fake.rulesetAttr, fake.createFlags, wantRuleset)
			}
			if exactV3HandledAccess != 0x7fff {
				t.Fatalf("exactV3HandledAccess = %#x, want 0x7fff", exactV3HandledAccess)
			}

			wantRules := []fakePathRule{
				{path: "/a-ro", allowed: readOnlyV3Access},
				{path: "/z-ro", allowed: readOnlyV3Access},
				{path: "/a-rw", allowed: readWriteV3Access},
				{path: "/z-rw", allowed: readWriteV3Access},
				{path: "/dev/pts", allowed: llsyscall.AccessFSWriteFile},
				{path: "/dev/null", allowed: nullDeviceV3Access},
			}
			if !reflect.DeepEqual(fake.rules, wantRules) {
				t.Fatalf("path rules = %#v, want %#v", fake.rules, wantRules)
			}
			if readOnlyV3Access != llsyscall.AccessFSExecute|llsyscall.AccessFSReadFile|llsyscall.AccessFSReadDir {
				t.Fatalf("read-only access = %#x", readOnlyV3Access)
			}
			if readWriteV3Access != exactV3HandledAccess&^llsyscall.AccessFSRefer {
				t.Fatalf("read-write access = %#x, want exact V3 without REFER", readWriteV3Access)
			}
			if nullDeviceV3Access != llsyscall.AccessFSExecute|llsyscall.AccessFSReadFile|llsyscall.AccessFSWriteFile|llsyscall.AccessFSTruncate {
				t.Fatalf("null-device access = %#x", nullDeviceV3Access)
			}
			if privateDevptsPTYV3Access != llsyscall.AccessFSWriteFile {
				t.Fatalf("private-devpts PTY access = %#x, want only WRITE_FILE", privateDevptsPTYV3Access)
			}
			if privateDevptsPTYV3Access&(llsyscall.AccessFSMakeChar|llsyscall.AccessFSMakeDir|llsyscall.AccessFSRemoveDir|llsyscall.AccessFSRemoveFile|llsyscall.AccessFSTruncate|llsyscall.AccessFSRefer) != 0 {
				t.Fatalf("private-devpts PTY access contains creation, removal, truncate, or refer rights: %#x", privateDevptsPTYV3Access)
			}

			for _, opened := range fake.opened {
				wantFlags := unix.O_PATH | unix.O_CLOEXEC | unix.O_NOFOLLOW
				if opened.path == "/dev/pts" {
					wantFlags = unix.O_RDONLY | unix.O_DIRECTORY | unix.O_CLOEXEC | unix.O_NOFOLLOW
				}
				if opened.flags != wantFlags || opened.mode != 0 {
					t.Fatalf("open %q flags=%#x mode=%#o, want %#x mode=0", opened.path, opened.flags, opened.mode, wantFlags)
				}
			}
			if got, want := fake.closed, []int{11, 12, 13, 14, 15, 10, 16}; !reflect.DeepEqual(got, want) {
				t.Fatalf("closed source descriptors = %#v, want %#v", got, want)
			}
			if !fake.cloexecSet || !fake.cloexecRead {
				t.Fatalf("CLOEXEC set/read = %t/%t, want both true", fake.cloexecSet, fake.cloexecRead)
			}
		})
	}
}

func TestPrepareV3RejectsUnverifiedPrivateDevptsPTY(t *testing.T) {
	tests := []struct {
		name       string
		fault      string
		wantClosed []int
	}{
		{name: "open-directory", fault: "open-devpts", wantClosed: []int{7}},
		{name: "inspect-directory", fault: "fstat-devpts", wantClosed: []int{10, 7}},
		{name: "directory-type", fault: "regular-devpts", wantClosed: []int{10, 7}},
		{name: "inspect-filesystem", fault: "fstatfs-devpts", wantClosed: []int{10, 7}},
		{name: "filesystem-type", fault: "wrong-devpts-filesystem", wantClosed: []int{10, 7}},
		{name: "inspect-parent", fault: "fstatat-devpts-parent", wantClosed: []int{10, 7}},
		{name: "mount-boundary", fault: "same-devpts-parent", wantClosed: []int{10, 7}},
		{name: "inspect-root", fault: "fstatat-devpts-root", wantClosed: []int{10, 7}},
		{name: "root-type", fault: "regular-devpts-root", wantClosed: []int{10, 7}},
		{name: "read-topology", fault: "readdir-devpts", wantClosed: []int{10, 7}},
		{name: "unexpected-slave", fault: "unexpected-devpts-entry", wantClosed: []int{10, 7}},
		{name: "open-ptmx-relative", fault: "open-ptmx", wantClosed: []int{10, 7}},
		{name: "inspect-ptmx", fault: "fstat-ptmx", wantClosed: []int{11, 10, 7}},
		{name: "ptmx-symlink", fault: "symlink-ptmx", wantClosed: []int{11, 10, 7}},
		{name: "ptmx-filesystem", fault: "wrong-ptmx-filesystem", wantClosed: []int{11, 10, 7}},
		{name: "ptmx-identity", fault: "wrong-ptmx-device", wantClosed: []int{11, 10, 7}},
		{name: "close-ptmx", fault: "close-ptmx", wantClosed: []int{11, 10, 7}},
		{name: "add-rule", fault: "add-devpts", wantClosed: []int{11, 10, 7}},
		{name: "close-directory", fault: "close-devpts", wantClosed: []int{11, 10, 7}},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			fake := newPrepareV3Fake(3)
			fake.fault = test.fault
			_, err := prepareV3WithOps(Policy{AllowPrivateDevptsPTY: true}, fake.ops())
			if !errors.Is(err, ErrLandlockV3Unavailable) {
				t.Fatalf("prepareV3WithOps() error = %v, want ErrLandlockV3Unavailable", err)
			}
			if !reflect.DeepEqual(fake.closed, test.wantClosed) {
				t.Fatalf("closed descriptors = %#v, want %#v; events=%#v", fake.closed, test.wantClosed, fake.events)
			}
			if len(fake.openFDs) != 0 {
				t.Fatalf("private-devpts failure leaked open FDs: %#v", fake.openFDs)
			}
		})
	}
}

func TestPrepareV3RejectsBroadDevptsPolicyOverlap(t *testing.T) {
	for _, policy := range []Policy{
		{ReadOnlyPaths: []string{"/dev/pts"}, AllowPrivateDevptsPTY: true},
		{ReadWritePaths: []string{"/"}, AllowPrivateDevptsPTY: true},
		{ReadWritePaths: []string{"/dev"}, AllowPrivateDevptsPTY: true},
		{ReadWritePaths: []string{"/dev/pts"}, AllowPrivateDevptsPTY: true},
		{ReadWritePaths: []string{"/dev/pts/injected"}, AllowPrivateDevptsPTY: true},
	} {
		fake := newPrepareV3Fake(3)
		_, err := prepareV3WithOps(policy, fake.ops())
		if !errors.Is(err, ErrLandlockV3Unavailable) {
			t.Fatalf("prepareV3WithOps(%#v) error = %v, want ErrLandlockV3Unavailable", policy, err)
		}
		if !reflect.DeepEqual(fake.events, []string{"abi"}) {
			t.Fatalf("overlapping policy operations = %#v, want only ABI query", fake.events)
		}
	}
}

func TestPrepareV3RejectsNonCanonicalPolicyPathsBeforeCreatingRuleset(t *testing.T) {
	for _, path := range []string{
		"/dev/../dev/pts",
		"/tmp/../dev/pts",
		"//dev/pts",
		"/dev/./pts",
		"/dev//pts",
	} {
		fake := newPrepareV3Fake(3)
		_, err := prepareV3WithOps(Policy{
			ReadWritePaths:        []string{path},
			AllowPrivateDevptsPTY: true,
		}, fake.ops())
		if !errors.Is(err, ErrLandlockV3Unavailable) {
			t.Fatalf("prepareV3WithOps(%q) error = %v, want ErrLandlockV3Unavailable", path, err)
		}
		if !reflect.DeepEqual(fake.events, []string{"abi"}) {
			t.Fatalf("non-canonical policy %q operations = %#v, want only ABI query", path, fake.events)
		}
	}
}

func TestPrepareV3RejectsPhysicalDevptsWriteAliases(t *testing.T) {
	for _, path := range []string{"/bind/devpts", "/bind/dev", "/bind/root"} {
		fake := newPrepareV3Fake(3)
		_, err := prepareV3WithOps(Policy{
			ReadWritePaths:        []string{path},
			AllowPrivateDevptsPTY: true,
		}, fake.ops())
		if !errors.Is(err, ErrLandlockV3Unavailable) {
			t.Fatalf("prepareV3WithOps(%q) error = %v, want ErrLandlockV3Unavailable", path, err)
		}
		for _, rule := range fake.rules {
			if rule.path == path {
				t.Fatalf("physical alias %q received generic writable rule %#x", path, rule.allowed)
			}
		}
		if got, want := fake.closed, []int{11, 12, 10, 7}; !reflect.DeepEqual(got, want) {
			t.Fatalf("physical alias %q closed descriptors = %#v, want %#v", path, got, want)
		}
		if len(fake.openFDs) != 0 {
			t.Fatalf("physical alias %q leaked open FDs: %#v", path, fake.openFDs)
		}
	}
}

func TestOpenRulePathRejectsIntermediateMagicLink(t *testing.T) {
	fd, err := openRulePath(
		"/proc/self/root/dev/pts",
		unix.O_PATH|unix.O_CLOEXEC|unix.O_NOFOLLOW,
		0,
	)
	if err == nil {
		_ = unix.Close(fd)
		t.Fatal("openRulePath() followed /proc/self/root magic link")
	}
	if !errors.Is(err, unix.ELOOP) {
		t.Fatalf("openRulePath() error = %v, want ELOOP", err)
	}
}

func TestPrepareV3PrivateDevptsAllowsDisjointDevWritePath(t *testing.T) {
	fake := newPrepareV3Fake(3)
	prepared, err := prepareV3WithOps(Policy{
		ReadWritePaths:        []string{"/dev/shm"},
		AllowPrivateDevptsPTY: true,
	}, fake.ops())
	if err != nil {
		t.Fatalf("prepareV3WithOps() error = %v", err)
	}
	if prepared.rulesetFD != fake.rulesetFD {
		t.Fatalf("prepared ruleset FD = %d, want %d", prepared.rulesetFD, fake.rulesetFD)
	}
}

func TestPrepareV3ClosesEveryOwnedDescriptorOnFailure(t *testing.T) {
	tests := []struct {
		name       string
		fault      string
		rulesetFD  int
		wantClosed []int
	}{
		{name: "create-ruleset", fault: "create", rulesetFD: 7},
		{name: "ruleset-fd-below-three", rulesetFD: 2, wantClosed: []int{2}},
		{name: "ruleset-fd-at-uint32-max", rulesetFD: int(^uint32(0)), wantClosed: []int{int(^uint32(0))}},
		{name: "open-path", fault: "open", rulesetFD: 7, wantClosed: []int{7}},
		{name: "opened-fd-fstat", fault: "fstat", rulesetFD: 7, wantClosed: []int{10, 7}},
		{name: "symlink-source", fault: "symlink", rulesetFD: 7, wantClosed: []int{10, 7}},
		{name: "regular-file-directory-source", fault: "regular", rulesetFD: 7, wantClosed: []int{10, 7}},
		{name: "wrong-null-device", fault: "wrong-device", rulesetFD: 7, wantClosed: []int{10, 11, 12, 7}},
		{name: "add-rule", fault: "add", rulesetFD: 7, wantClosed: []int{10, 7}},
		{name: "source-close", fault: "close-source", rulesetFD: 7, wantClosed: []int{10, 7}},
		{name: "set-cloexec", fault: "set-cloexec", rulesetFD: 7, wantClosed: []int{10, 11, 12, 7}},
		{name: "get-cloexec", fault: "get-cloexec", rulesetFD: 7, wantClosed: []int{10, 11, 12, 7}},
		{name: "cloexec-not-set", fault: "cloexec-false", rulesetFD: 7, wantClosed: []int{10, 11, 12, 7}},
	}

	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			fake := newPrepareV3Fake(3)
			fake.fault = test.fault
			fake.rulesetFD = test.rulesetFD
			_, err := prepareV3WithOps(Policy{
				ReadOnlyPaths:  []string{"/ro"},
				ReadWritePaths: []string{"/rw"},
			}, fake.ops())
			if err == nil {
				t.Fatal("prepareV3WithOps() error = nil, want injected failure")
			}
			if !reflect.DeepEqual(fake.closed, test.wantClosed) {
				t.Fatalf("closed descriptors = %#v, want %#v; events=%#v", fake.closed, test.wantClosed, fake.events)
			}
		})
	}
}

func TestPrepareExecVectors(t *testing.T) {
	executable, err := os.Executable()
	if err != nil {
		t.Fatalf("resolve test executable: %v", err)
	}
	fake := newPrepareV3Fake(3)
	args := []string{executable, "unique argument"}
	environment := []string{"ALPHA=unique value", "EMPTY="}
	prepared, err := prepareRestrictedExecWithOps(ExecSpec{
		Path:   executable,
		Args:   args,
		Env:    environment,
		Policy: Policy{},
	}, fake.ops())
	if err != nil {
		t.Fatalf("prepareRestrictedExecWithOps() error = %v", err)
	}

	if got, want := string(prepared.pathStorage), executable+"\x00"; got != want {
		t.Fatalf("path storage = %q, want %q", got, want)
	}
	if len(prepared.argvStorage) != len(args) || len(prepared.argv) != len(args)+1 {
		t.Fatalf("argv storage/vector lengths = %d/%d, want %d/%d", len(prepared.argvStorage), len(prepared.argv), len(args), len(args)+1)
	}
	if len(prepared.envStorage) != len(environment) || len(prepared.envp) != len(environment)+1 {
		t.Fatalf("env storage/vector lengths = %d/%d, want %d/%d", len(prepared.envStorage), len(prepared.envp), len(environment), len(environment)+1)
	}
	for index, argument := range args {
		if got, want := string(prepared.argvStorage[index]), argument+"\x00"; got != want {
			t.Fatalf("argv storage %d = %q, want %q", index, got, want)
		}
		if prepared.argv[index] != &prepared.argvStorage[index][0] {
			t.Fatalf("argv pointer %d does not reference owned storage", index)
		}
	}
	for index, entry := range environment {
		if got, want := string(prepared.envStorage[index]), entry+"\x00"; got != want {
			t.Fatalf("env storage %d = %q, want %q", index, got, want)
		}
		if prepared.envp[index] != &prepared.envStorage[index][0] {
			t.Fatalf("env pointer %d does not reference owned storage", index)
		}
	}
	if prepared.argv[len(args)] != nil || prepared.envp[len(environment)] != nil {
		t.Fatal("raw argv/environment vectors are not nil-terminated")
	}
	if prepared.argv[0] == &prepared.pathStorage[0] {
		t.Fatal("path and argv storage unexpectedly alias")
	}
	if prepared.rulesetFD != fake.rulesetFD || prepared.upperFirst != uint32(fake.rulesetFD+1) ||
		prepared.lowerLast != uint32(fake.rulesetFD-1) || !prepared.hasLower {
		t.Fatalf("descriptor geometry = fd %d upper %d lower %d hasLower=%t", prepared.rulesetFD, prepared.upperFirst, prepared.lowerLast, prepared.hasLower)
	}
	if prepared.fault != terminalFaultNone {
		t.Fatalf("production terminal fault = %d, want none", prepared.fault)
	}
	if unsafe.Pointer(prepared.argv[0]) == nil || unsafe.Pointer(prepared.envp[0]) == nil {
		t.Fatal("owned raw vector contains an unexpected nil pointer")
	}

	args[1] = "mutated"
	environment[0] = "ALPHA=mutated"
	if got := string(prepared.argvStorage[1]); got != "unique argument\x00" {
		t.Fatalf("argv storage aliased caller slice: %q", got)
	}
	if got := string(prepared.envStorage[0]); got != "ALPHA=unique value\x00" {
		t.Fatalf("environment storage aliased caller slice: %q", got)
	}

	invalid := []struct {
		name string
		spec ExecSpec
	}{
		{name: "path-NUL", spec: ExecSpec{Path: executable + "\x00", Args: []string{executable + "\x00"}}},
		{name: "argv-NUL", spec: ExecSpec{Path: executable, Args: []string{executable, "bad\x00arg"}}},
		{name: "environment-NUL", spec: ExecSpec{Path: executable, Args: []string{executable}, Env: []string{"BAD=bad\x00value"}}},
		{name: "duplicate-environment", spec: ExecSpec{Path: executable, Args: []string{executable}, Env: []string{"DUP=one", "DUP=two"}}},
	}
	for _, test := range invalid {
		t.Run(test.name, func(t *testing.T) {
			invalidFake := newPrepareV3Fake(3)
			if _, err := prepareRestrictedExecWithOps(test.spec, invalidFake.ops()); !errors.Is(err, ErrRestrictedExec) {
				t.Fatalf("prepareRestrictedExecWithOps() error = %v, want ErrRestrictedExec", err)
			}
			if len(invalidFake.events) != 0 {
				t.Fatalf("invalid vectors reached ruleset operations: %#v", invalidFake.events)
			}
		})
	}
}

func TestTerminalFakeRawOperationOrder(t *testing.T) {
	type call struct {
		first uint32
		last  uint32
		flags uint32
	}
	tests := []struct {
		name string
		fd   int
		want []call
	}{
		{name: "ruleset-fd-three", fd: 3, want: []call{{first: 4, last: ^uint32(0), flags: unix.CLOSE_RANGE_UNSHARE}}},
		{name: "ruleset-fd-above-three", fd: 7, want: []call{
			{first: 8, last: ^uint32(0), flags: unix.CLOSE_RANGE_UNSHARE},
			{first: 3, last: 6, flags: 0},
		}},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			var got []call
			errno := closeInheritedExceptWith(test.fd, func(first, last, flags uint32) unix.Errno {
				got = append(got, call{first: first, last: last, flags: flags})
				return 0
			})
			if errno != 0 {
				t.Fatalf("closeInheritedExceptWith() errno = %v", errno)
			}
			if !reflect.DeepEqual(got, test.want) {
				t.Fatalf("close-range calls = %#v, want %#v", got, test.want)
			}
		})
	}
}

func TestExecutePreparedPreservesRulesetFD(t *testing.T) {
	switch os.Getenv(testPreserveRulesetMode) {
	case "target":
		var decoys []int
		switch os.Getenv(testPreserveRulesetCase) {
		case "fd-three":
			decoys = []int{testUpperDecoyFD}
		case "fd-above-three":
			decoys = []int{testLowerDecoyFD, testUpperDecoyFD}
		default:
			t.Fatalf("unknown preserve-ruleset target case %q", os.Getenv(testPreserveRulesetCase))
		}
		for _, fd := range decoys {
			if _, err := unix.FcntlInt(uintptr(fd), unix.F_GETFD, 0); !errors.Is(err, unix.EBADF) {
				t.Fatalf("decoy FD %d after raw exec: error=%v, want EBADF", fd, err)
			}
		}
		return
	case "launcher":
		runPreservedRulesetLauncher(t, os.Getenv(testPreserveRulesetCase))
		return
	}

	tests := []struct {
		name      string
		rulesetFD int
		want      []recordedCloseRange
	}{
		{
			name:      "fd-three",
			rulesetFD: 3,
			want: []recordedCloseRange{
				{first: 4, last: ^uint32(0), flags: unix.CLOSE_RANGE_UNSHARE},
			},
		},
		{
			name:      "fd-above-three",
			rulesetFD: testMovedRulesetFD,
			want: []recordedCloseRange{
				{first: testMovedRulesetFD + 1, last: ^uint32(0), flags: unix.CLOSE_RANGE_UNSHARE},
				{first: 3, last: testMovedRulesetFD - 1, flags: 0},
			},
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			requireExactCloseRanges(t, test.rulesetFD, test.want)
			command := exec.Command(os.Args[0], "-test.run=^TestExecutePreparedPreservesRulesetFD$")
			command.Env = []string{
				testPreserveRulesetMode + "=launcher",
				testPreserveRulesetCase + "=" + test.name,
			}
			if output, err := command.CombinedOutput(); err != nil {
				t.Fatalf("preserved-ruleset helper: %v; output=%q", err, output)
			}
		})
	}
}

func runPreservedRulesetLauncher(t *testing.T, testCase string) {
	t.Helper()

	executable, err := os.Executable()
	if err != nil {
		t.Fatalf("resolve helper executable: %v", err)
	}

	switch testCase {
	case "fd-three":
		if err := unix.Close(3); err != nil && !errors.Is(err, unix.EBADF) {
			t.Fatalf("free descriptor 3: %v", err)
		}
	case "fd-above-three":
		if err := installDescriptorAt("/dev/zero", 3); err != nil {
			t.Fatalf("occupy descriptor 3: %v", err)
		}
	default:
		t.Fatalf("unknown preserve-ruleset launcher case %q", testCase)
	}

	preparedPtr, err := prepareRestrictedExec(ExecSpec{
		Path: executable,
		Args: []string{executable, "-test.run=^TestExecutePreparedPreservesRulesetFD$"},
		Env: []string{
			testPreserveRulesetMode + "=target",
			testPreserveRulesetCase + "=" + testCase,
		},
		Policy: Policy{ReadOnlyPaths: existingTestDirectories(
			"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(executable),
		)},
	})
	if err != nil {
		t.Fatalf("prepare restricted exec: %v", err)
	}

	switch testCase {
	case "fd-three":
		if preparedPtr.rulesetFD != 3 {
			t.Fatalf("ruleset FD = %d, want 3 after freeing descriptor 3", preparedPtr.rulesetFD)
		}
	case "fd-above-three":
		if preparedPtr.rulesetFD <= 3 {
			t.Fatalf("ruleset FD = %d, want above occupied descriptor 3", preparedPtr.rulesetFD)
		}
		if preparedPtr.rulesetFD != testMovedRulesetFD {
			if err := unix.Dup3(preparedPtr.rulesetFD, testMovedRulesetFD, unix.O_CLOEXEC); err != nil {
				t.Fatalf("move ruleset FD to %d: %v", testMovedRulesetFD, err)
			}
			if err := unix.Close(preparedPtr.rulesetFD); err != nil {
				t.Fatalf("close original ruleset FD: %v", err)
			}
			preparedPtr.rulesetFD = testMovedRulesetFD
			preparedPtr.upperFirst = testMovedRulesetFD + 1
			preparedPtr.lowerLast = testMovedRulesetFD - 1
			preparedPtr.hasLower = true
		}
		if err := installDescriptorAt("/dev/zero", testLowerDecoyFD); err != nil {
			t.Fatalf("install lower decoy: %v", err)
		}
	}
	if err := installDescriptorAt("/dev/zero", testUpperDecoyFD); err != nil {
		t.Fatalf("install upper decoy: %v", err)
	}

	executePrepared(preparedPtr)
}

func TestCloseRangeUnshareLeavesSiblingDescriptorUsable(t *testing.T) {
	wantRanges := []recordedCloseRange{
		{first: testMovedRulesetFD + 1, last: ^uint32(0), flags: unix.CLOSE_RANGE_UNSHARE},
		{first: 3, last: testMovedRulesetFD - 1, flags: 0},
	}
	requireExactCloseRanges(t, testMovedRulesetFD, wantRanges)

	if os.Getenv(testCloseRangeUnshareMode) == "child" {
		runCloseRangeUnshareChild()
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer cancel()
	command := exec.CommandContext(ctx, os.Args[0], "-test.run=^TestCloseRangeUnshareLeavesSiblingDescriptorUsable$")
	command.Env = []string{testCloseRangeUnshareMode + "=child"}
	output, err := command.CombinedOutput()
	if errors.Is(ctx.Err(), context.DeadlineExceeded) {
		t.Fatalf("close-range unshare helper timed out; output=%q", output)
	}
	if err != nil {
		t.Fatalf("close-range unshare helper: %v; output=%q", err, output)
	}
}

func runCloseRangeUnshareChild() {
	for _, descriptor := range []struct {
		path string
		fd   int
	}{
		{path: "/dev/null", fd: testMovedRulesetFD},
		{path: "/dev/zero", fd: testLowerDecoyFD},
		{path: "/dev/zero", fd: testUpperDecoyFD},
	} {
		if err := installDescriptorAt(descriptor.path, descriptor.fd); err != nil {
			closeRangeChildFailure("install descriptor", err)
		}
	}

	type siblingResult struct {
		lower error
		upper error
	}
	ready := make(chan struct{})
	inspect := make(chan struct{})
	result := make(chan siblingResult, 1)
	go func() {
		runtime.LockOSThread()
		close(ready)
		<-inspect
		var lowerStat, upperStat unix.Stat_t
		result <- siblingResult{
			lower: unix.Fstat(testLowerDecoyFD, &lowerStat),
			upper: unix.Fstat(testUpperDecoyFD, &upperStat),
		}
	}()
	<-ready

	runtime.LockOSThread()
	if errno := closeInheritedExcept(testMovedRulesetFD); errno != 0 {
		closeRangeChildFailure("close inherited descriptors", errno)
	}
	var preserved unix.Stat_t
	if err := unix.Fstat(testMovedRulesetFD, &preserved); err != nil {
		closeRangeChildFailure("fstat preserved descriptor", err)
	}
	for _, fd := range []int{testLowerDecoyFD, testUpperDecoyFD} {
		if _, err := unix.FcntlInt(uintptr(fd), unix.F_GETFD, 0); !errors.Is(err, unix.EBADF) {
			closeRangeChildFailure("decoy remained in caller table", fmt.Errorf("fd %d: %v", fd, err))
		}
	}
	close(inspect)
	sibling := <-result
	if sibling.lower != nil || sibling.upper != nil {
		closeRangeChildFailure("sibling lost old-table descriptor", fmt.Errorf("lower=%v upper=%v", sibling.lower, sibling.upper))
	}
	os.Exit(0)
}

func closeRangeChildFailure(stage string, err error) {
	_, _ = fmt.Fprintf(os.Stderr, "%s: %v\n", stage, err)
	os.Exit(17)
}

type recordedCloseRange struct {
	first uint32
	last  uint32
	flags uint32
}

func requireExactCloseRanges(t *testing.T, rulesetFD int, want []recordedCloseRange) {
	t.Helper()

	var got []recordedCloseRange
	errno := closeInheritedExceptWith(rulesetFD, func(first, last, flags uint32) unix.Errno {
		got = append(got, recordedCloseRange{first: first, last: last, flags: flags})
		return 0
	})
	if errno != 0 {
		t.Fatalf("closeInheritedExceptWith(%d) errno = %v", rulesetFD, errno)
	}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("close-range calls for FD %d = %#v, want %#v", rulesetFD, got, want)
	}
}

func installDescriptorAt(path string, target int) error {
	fd, err := unix.Open(path, unix.O_RDONLY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return err
	}
	if fd == target {
		_, err = unix.FcntlInt(uintptr(fd), unix.F_SETFD, 0)
		return err
	}
	defer unix.Close(fd)
	return unix.Dup3(fd, target, 0)
}

func TestExecRestrictedDoesNotLeakReusedDecoyFD(t *testing.T) {
	switch os.Getenv(testDecoyExecMode) {
	case "target":
		lowerDev := requiredUintEnvironment(t, "README_TERMINAL_DEMO_TEST_LOWER_DEV")
		lowerIno := requiredUintEnvironment(t, "README_TERMINAL_DEMO_TEST_LOWER_INO")
		upperDev := requiredUintEnvironment(t, "README_TERMINAL_DEMO_TEST_UPPER_DEV")
		upperIno := requiredUintEnvironment(t, "README_TERMINAL_DEMO_TEST_UPPER_INO")

		lowerClosed := requireOriginalDescriptionAbsent(t, 3, lowerDev, lowerIno)
		if lowerClosed {
			reusedFD, err := unix.Open("/dev/null", unix.O_RDONLY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
			if err != nil {
				t.Fatalf("reuse closed lower decoy FD: %v", err)
			}
			defer unix.Close(reusedFD)
			if reusedFD != 3 {
				t.Fatalf("reused lower descriptor = %d, want 3", reusedFD)
			}
			requireOriginalDescriptionAbsent(t, reusedFD, lowerDev, lowerIno)
		}
		requireOriginalDescriptionAbsent(t, testUpperDecoyFD, upperDev, upperIno)
		return

	case "launcher":
		lowerPath := os.Getenv(testDecoyLowerPath)
		upperPath := os.Getenv(testDecoyUpperPath)
		lowerDev, lowerIno := requiredPathIdentity(t, lowerPath)
		upperDev, upperIno := requiredPathIdentity(t, upperPath)
		if err := installDescriptorAt(lowerPath, 3); err != nil {
			t.Fatalf("install lower decoy at FD 3: %v", err)
		}
		if err := installDescriptorAt(upperPath, testUpperDecoyFD); err != nil {
			t.Fatalf("install upper decoy at FD %d: %v", testUpperDecoyFD, err)
		}

		executable, err := os.Executable()
		if err != nil {
			t.Fatalf("resolve helper executable: %v", err)
		}
		err = ExecRestricted(ExecSpec{
			Path: executable,
			Args: []string{executable, "-test.run=^TestExecRestrictedDoesNotLeakReusedDecoyFD$"},
			Env: []string{
				testDecoyExecMode + "=target",
				"README_TERMINAL_DEMO_TEST_LOWER_DEV=" + strconv.FormatUint(lowerDev, 10),
				"README_TERMINAL_DEMO_TEST_LOWER_INO=" + strconv.FormatUint(lowerIno, 10),
				"README_TERMINAL_DEMO_TEST_UPPER_DEV=" + strconv.FormatUint(upperDev, 10),
				"README_TERMINAL_DEMO_TEST_UPPER_INO=" + strconv.FormatUint(upperIno, 10),
			},
			Policy: Policy{ReadOnlyPaths: existingTestDirectories(
				"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(executable),
			)},
		})
		if err != nil {
			t.Fatalf("ExecRestricted() error = %v", err)
		}
		t.Fatal("ExecRestricted returned after successful preflight")
	}

	directory := t.TempDir()
	lowerPath := filepath.Join(directory, "lower-decoy")
	upperPath := filepath.Join(directory, "upper-decoy")
	if err := os.WriteFile(lowerPath, []byte("lower"), 0o600); err != nil {
		t.Fatalf("write lower decoy: %v", err)
	}
	if err := os.WriteFile(upperPath, []byte("upper"), 0o600); err != nil {
		t.Fatalf("write upper decoy: %v", err)
	}
	command := exec.Command(os.Args[0], "-test.run=^TestExecRestrictedDoesNotLeakReusedDecoyFD$")
	command.Env = []string{
		testDecoyExecMode + "=launcher",
		testDecoyLowerPath + "=" + lowerPath,
		testDecoyUpperPath + "=" + upperPath,
	}
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("decoy raw-exec helper: %v; output=%q", err, output)
	}
}

func requiredPathIdentity(t *testing.T, path string) (uint64, uint64) {
	t.Helper()

	var stat unix.Stat_t
	if err := unix.Stat(path, &stat); err != nil {
		t.Fatalf("stat decoy %q: %v", path, err)
	}
	return uint64(stat.Dev), stat.Ino
}

func requiredUintEnvironment(t *testing.T, name string) uint64 {
	t.Helper()

	value, err := strconv.ParseUint(os.Getenv(name), 10, 64)
	if err != nil {
		t.Fatalf("parse %s: %v", name, err)
	}
	return value
}

func requireOriginalDescriptionAbsent(t *testing.T, fd int, wantDev, wantIno uint64) bool {
	t.Helper()

	var stat unix.Stat_t
	err := unix.Fstat(fd, &stat)
	if errors.Is(err, unix.EBADF) {
		return true
	}
	if err != nil {
		t.Fatalf("fstat decoy FD %d: %v", fd, err)
	}
	if uint64(stat.Dev) == wantDev && stat.Ino == wantIno {
		t.Fatalf("original decoy file description leaked at FD %d", fd)
	}
	return false
}

func TestExecVectorsSurviveGCAndCheckptr(t *testing.T) {
	longArgument, longEnvironment := uniqueExecVectorValues()
	switch os.Getenv(testExecVectorMode) {
	case "target":
		if len(os.Args) != 3 || os.Args[2] != longArgument {
			t.Fatalf("post-exec argv mismatch: argc=%d final-bytes=%d", len(os.Args), len(os.Args[len(os.Args)-1]))
		}
		if got := os.Getenv("README_TERMINAL_DEMO_TEST_LONG_VECTOR"); got != longEnvironment {
			t.Fatalf("post-exec environment bytes = %d, want %d", len(got), len(longEnvironment))
		}
		return

	case "launcher":
		executable, err := os.Executable()
		if err != nil {
			t.Fatalf("resolve helper executable: %v", err)
		}
		preparedPtr, err := prepareRestrictedExec(ExecSpec{
			Path: executable,
			Args: []string{executable, "-test.run=^TestExecVectorsSurviveGCAndCheckptr$", longArgument},
			Env: []string{
				testExecVectorMode + "=target",
				"GODEBUG=checkptr=2",
				"README_TERMINAL_DEMO_TEST_LONG_VECTOR=" + longEnvironment,
			},
			Policy: Policy{ReadOnlyPaths: existingTestDirectories(
				"/usr", "/etc", "/proc", "/sys", "/dev", filepath.Dir(executable),
			)},
		})
		if err != nil {
			t.Fatalf("prepare restricted exec: %v", err)
		}

		longArgument = ""
		longEnvironment = ""
		for round := 0; round < 8; round++ {
			churn := make([][]byte, 256)
			for index := range churn {
				churn[index] = make([]byte, 2048)
				churn[index][0] = byte(round + index)
			}
			runtime.GC()
			runtime.KeepAlive(churn)
		}
		executePrepared(preparedPtr)
		return
	}

	command := exec.Command(os.Args[0], "-test.run=^TestExecVectorsSurviveGCAndCheckptr$")
	command.Env = []string{
		testExecVectorMode + "=launcher",
		"GODEBUG=checkptr=2",
	}
	if output, err := command.CombinedOutput(); err != nil {
		t.Fatalf("GC/checkptr raw-exec helper: %v; output=%q", err, output)
	}
}

func uniqueExecVectorValues() (string, string) {
	return "argument-" + strings.Repeat("a1B2c3D4", 4096),
		"environment-" + strings.Repeat("Z9y8X7w6", 4096)
}

type fakeOpen struct {
	path  string
	flags int
	mode  uint32
}

type fakePathRule struct {
	path    string
	allowed uint64
}

type prepareV3Fake struct {
	abi         int
	rulesetFD   int
	fault       string
	nextFD      int
	fdPaths     map[int]string
	events      []string
	opened      []fakeOpen
	rules       []fakePathRule
	closed      []int
	rulesetAttr llsyscall.RulesetAttr
	createFlags int
	cloexecSet  bool
	cloexecRead bool
	fstatSeen   map[int]bool
	openFDs     map[int]bool
}

func newPrepareV3Fake(abi int) *prepareV3Fake {
	return &prepareV3Fake{
		abi:       abi,
		rulesetFD: 7,
		nextFD:    10,
		fdPaths:   make(map[int]string),
		fstatSeen: make(map[int]bool),
		openFDs:   make(map[int]bool),
	}
}

func (fake *prepareV3Fake) ops() prepareV3Ops {
	return prepareV3Ops{
		getABI: func() (int, error) {
			fake.events = append(fake.events, "abi")
			return fake.abi, nil
		},
		createRuleset: func(attr *llsyscall.RulesetAttr, flags int) (int, error) {
			fake.events = append(fake.events, "create")
			fake.rulesetAttr = *attr
			fake.createFlags = flags
			if fake.fault == "create" {
				return -1, unix.EIO
			}
			return fake.rulesetFD, nil
		},
		openPath: func(path string, flags int, mode uint32) (int, error) {
			fake.events = append(fake.events, "open:"+path)
			if fake.fault == "open" || fake.fault == "open-devpts" && path == "/dev/pts" {
				return -1, unix.EIO
			}
			fd := fake.nextFD
			fake.nextFD++
			fake.fdPaths[fd] = path
			fake.openFDs[fd] = true
			fake.opened = append(fake.opened, fakeOpen{path: path, flags: flags, mode: mode})
			return fd, nil
		},
		openPathAt: func(dirFD int, path string, flags int, mode uint32) (int, error) {
			fake.events = append(fake.events, "openat:"+strconv.Itoa(dirFD)+":"+path)
			if fake.fault == "open-ptmx" {
				return -1, unix.EIO
			}
			if fake.fdPaths[dirFD] != "/dev/pts" || path != "ptmx" {
				return -1, unix.EINVAL
			}
			fd := fake.nextFD
			fake.nextFD++
			fullPath := "/dev/pts/ptmx"
			fake.fdPaths[fd] = fullPath
			fake.openFDs[fd] = true
			fake.opened = append(fake.opened, fakeOpen{path: fullPath, flags: flags, mode: mode})
			return fd, nil
		},
		fstat: func(fd int, stat *unix.Stat_t) error {
			fake.events = append(fake.events, "fstat:"+strconv.Itoa(fd))
			fake.fstatSeen[fd] = true
			path := fake.fdPaths[fd]
			if fake.fault == "fstat" || fake.fault == "fstat-devpts" && path == "/dev/pts" || fake.fault == "fstat-ptmx" && path == "/dev/pts/ptmx" {
				return unix.EIO
			}
			switch {
			case fake.fault == "symlink":
				stat.Mode = unix.S_IFLNK | 0o777
			case fake.fault == "symlink-ptmx" && path == "/dev/pts/ptmx":
				stat.Mode = unix.S_IFLNK | 0o777
			case fake.fault == "regular" || fake.fault == "regular-devpts" && path == "/dev/pts":
				stat.Mode = unix.S_IFREG | 0o644
			case path == "/dev/null":
				stat.Mode = unix.S_IFCHR | 0o666
				stat.Rdev = unix.Mkdev(1, 3)
				if fake.fault == "wrong-device" {
					stat.Rdev = unix.Mkdev(1, 5)
				}
			case path == "/dev/pts/ptmx":
				stat.Mode = unix.S_IFCHR | 0o666
				stat.Rdev = unix.Mkdev(5, 2)
				stat.Dev = 183
				if fake.fault == "wrong-ptmx-device" {
					stat.Rdev = unix.Mkdev(1, 5)
				}
				if fake.fault == "wrong-ptmx-filesystem" {
					stat.Dev = 999
				}
			case path == "/bind/devpts":
				stat.Mode = unix.S_IFDIR | 0o755
				stat.Dev = 183
				stat.Ino = 1
			case path == "/bind/dev":
				stat.Mode = unix.S_IFDIR | 0o755
				stat.Dev = 182
				stat.Ino = 2
			case path == "/bind/root":
				stat.Mode = unix.S_IFDIR | 0o755
				stat.Dev = 181
				stat.Ino = 3
			default:
				stat.Mode = unix.S_IFDIR | 0o755
				if path == "/dev/pts" {
					stat.Dev = 183
					stat.Ino = 1
				}
			}
			return nil
		},
		fstatfs: func(fd int, stat *unix.Statfs_t) error {
			fake.events = append(fake.events, "fstatfs:"+strconv.Itoa(fd))
			if fake.fault == "fstatfs-devpts" {
				return unix.EIO
			}
			stat.Type = devptsSuperMagic
			if fake.fault == "wrong-devpts-filesystem" {
				stat.Type = unix.TMPFS_MAGIC
			}
			return nil
		},
		fstatAt: func(dirFD int, path string, stat *unix.Stat_t, flags int) error {
			fake.events = append(fake.events, "fstatat:"+strconv.Itoa(dirFD)+":"+path)
			if fake.fdPaths[dirFD] != "/dev/pts" || flags != unix.AT_SYMLINK_NOFOLLOW {
				return unix.EINVAL
			}
			if fake.fault == "fstatat-devpts-parent" && path == ".." || fake.fault == "fstatat-devpts-root" && path == "../.." {
				return unix.EIO
			}
			stat.Mode = unix.S_IFDIR | 0o755
			switch path {
			case "..":
				stat.Dev = 182
				stat.Ino = 2
				if fake.fault == "same-devpts-parent" {
					stat.Dev = 183
				}
			case "../..":
				stat.Dev = 181
				stat.Ino = 3
				if fake.fault == "regular-devpts-root" {
					stat.Mode = unix.S_IFREG | 0o644
				}
			default:
				return unix.EINVAL
			}
			return nil
		},
		readDirNames: func(fd int) ([]string, error) {
			fake.events = append(fake.events, "readdir:"+strconv.Itoa(fd))
			if fake.fdPaths[fd] != "/dev/pts" {
				return nil, unix.EINVAL
			}
			if fake.fault == "readdir-devpts" {
				return nil, unix.EIO
			}
			if fake.fault == "unexpected-devpts-entry" {
				return []string{"0", "ptmx"}, nil
			}
			return []string{"ptmx"}, nil
		},
		addPathRule: func(rulesetFD int, attr *llsyscall.PathBeneathAttr, flags int) error {
			fake.events = append(fake.events, "add:"+strconv.Itoa(attr.ParentFd))
			if rulesetFD != fake.rulesetFD || flags != 0 || !fake.fstatSeen[attr.ParentFd] || !fake.openFDs[attr.ParentFd] {
				return unix.EINVAL
			}
			fake.rules = append(fake.rules, fakePathRule{path: fake.fdPaths[attr.ParentFd], allowed: attr.AllowedAccess})
			if fake.fault == "add" || fake.fault == "add-devpts" && fake.fdPaths[attr.ParentFd] == "/dev/pts" {
				return unix.EIO
			}
			return nil
		},
		setCLOEXEC: func(fd int) error {
			fake.events = append(fake.events, "set-cloexec")
			fake.cloexecSet = true
			if fake.fault == "set-cloexec" {
				return unix.EIO
			}
			return nil
		},
		getCLOEXEC: func(fd int) (bool, error) {
			fake.events = append(fake.events, "get-cloexec")
			fake.cloexecRead = true
			if fake.fault == "get-cloexec" {
				return false, unix.EIO
			}
			return fake.fault != "cloexec-false", nil
		},
		closeFD: func(fd int) error {
			fake.events = append(fake.events, "close:"+strconv.Itoa(fd))
			fake.closed = append(fake.closed, fd)
			delete(fake.openFDs, fd)
			if fake.fault == "close-source" && fd >= 10 {
				return unix.EIO
			}
			if fake.fault == "close-ptmx" && fake.fdPaths[fd] == "/dev/pts/ptmx" {
				return unix.EIO
			}
			if fake.fault == "close-devpts" && fake.fdPaths[fd] == "/dev/pts" {
				return unix.EIO
			}
			return nil
		},
	}
}
