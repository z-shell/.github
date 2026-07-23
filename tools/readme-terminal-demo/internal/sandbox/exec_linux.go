package sandbox

import (
	"fmt"
	"runtime"
	"strings"
	"unsafe"

	"golang.org/x/sys/unix"
)

type terminalFault uint8

const (
	terminalFaultNone terminalFault = iota
	terminalFaultUpperClose
	terminalFaultLowerClose
	terminalFaultNoNewPrivs
	terminalFaultRestrictSelf
	terminalFaultRulesetClose
	terminalFaultTIDMismatch
	terminalFaultExecve
)

type preparedExec struct {
	pathStorage []byte
	argvStorage [][]byte
	envStorage  [][]byte
	argv        []*byte
	envp        []*byte
	rulesetFD   int
	upperFirst  uint32
	lowerLast   uint32
	hasLower    bool
	fault       terminalFault
}

// ExecRestricted completes every fallible input, vector, and policy preflight
// before entering the non-returning current-thread terminal sequence.
func ExecRestricted(spec ExecSpec) error {
	preparedPtr, err := prepareRestrictedExec(spec)
	if err != nil {
		return err
	}
	executePrepared(preparedPtr)
	exitGroup(runtimeFailureExitCode)
	for {
	}
}

func prepareRestrictedExec(spec ExecSpec) (*preparedExec, error) {
	return prepareRestrictedExecWithOps(spec, productionPrepareV3Ops)
}

func prepareRestrictedExecWithOps(spec ExecSpec, ops prepareV3Ops) (*preparedExec, error) {
	if err := validateExecPath(spec.Path); err != nil {
		return nil, err
	}
	if err := validateExecArgs(spec.Path, spec.Args); err != nil {
		return nil, err
	}
	if err := validateExecEnvironment(spec.Env); err != nil {
		return nil, err
	}

	pathStorage := ownedCString(spec.Path)
	argvStorage, argv := ownedCStringVector(spec.Args)
	envStorage, envp := ownedCStringVector(spec.Env)
	policy, err := prepareV3WithOps(spec.Policy, ops)
	if err != nil {
		return nil, err
	}

	return &preparedExec{
		pathStorage: pathStorage,
		argvStorage: argvStorage,
		envStorage:  envStorage,
		argv:        argv,
		envp:        envp,
		rulesetFD:   policy.rulesetFD,
		upperFirst:  uint32(policy.rulesetFD + 1),
		lowerLast:   uint32(policy.rulesetFD - 1),
		hasLower:    policy.rulesetFD > 3,
		fault:       terminalFaultNone,
	}, nil
}

func ownedCString(value string) []byte {
	storage := make([]byte, len(value)+1)
	copy(storage, value)
	return storage
}

func ownedCStringVector(values []string) ([][]byte, []*byte) {
	storage := make([][]byte, len(values))
	vector := make([]*byte, len(values)+1)
	for index, value := range values {
		storage[index] = ownedCString(value)
		vector[index] = &storage[index][0]
	}
	return storage, vector
}

func validateExecPath(path string) error {
	if path == "" || strings.ContainsRune(path, 0) || !strings.HasPrefix(path, "/") || path != strings.TrimSuffix(path, "/") {
		return fmt.Errorf("%w: invalid target path", ErrRestrictedExec)
	}
	var stat unix.Stat_t
	if err := unix.Fstatat(unix.AT_FDCWD, path, &stat, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fmt.Errorf("%w: inspect target", ErrRestrictedExec)
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFREG || stat.Mode&0o111 == 0 {
		return fmt.Errorf("%w: target is not an executable regular file", ErrRestrictedExec)
	}
	return nil
}

func validateExecArgs(path string, args []string) error {
	if len(args) == 0 || args[0] != path {
		return fmt.Errorf("%w: invalid target argv", ErrRestrictedExec)
	}
	for _, arg := range args {
		if strings.ContainsRune(arg, 0) {
			return fmt.Errorf("%w: invalid target argv", ErrRestrictedExec)
		}
	}
	return nil
}

func validateExecEnvironment(environment []string) error {
	seen := make(map[string]struct{}, len(environment))
	for _, entry := range environment {
		if strings.ContainsRune(entry, 0) {
			return fmt.Errorf("%w: invalid target environment", ErrRestrictedExec)
		}
		name, _, ok := strings.Cut(entry, "=")
		if !ok || !validEnvironmentName(name) {
			return fmt.Errorf("%w: invalid target environment", ErrRestrictedExec)
		}
		if _, duplicate := seen[name]; duplicate {
			return fmt.Errorf("%w: duplicate target environment", ErrRestrictedExec)
		}
		seen[name] = struct{}{}
	}
	return nil
}

func validEnvironmentName(name string) bool {
	if name == "" || !environmentNameStart(name[0]) {
		return false
	}
	for index := 1; index < len(name); index++ {
		if !environmentNameStart(name[index]) && (name[index] < '0' || name[index] > '9') {
			return false
		}
	}
	return true
}

func environmentNameStart(character byte) bool {
	return character == '_' || character >= 'A' && character <= 'Z' || character >= 'a' && character <= 'z'
}

func executePrepared(preparedPtr *preparedExec) {
	runtime.LockOSThread()
	lockedTID, errno := rawGetTID()
	if errno != 0 {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault == terminalFaultUpperClose {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault == terminalFaultLowerClose {
		if rawCloseRangeCall(preparedPtr.upperFirst, ^uint32(0), unix.CLOSE_RANGE_UNSHARE) != 0 {
			exitGroup(runtimeFailureExitCode)
		}
		exitGroup(runtimeFailureExitCode)
	}
	if closeInheritedExcept(preparedPtr.rulesetFD) != 0 {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault == terminalFaultNoNewPrivs || rawNoNewPrivs() != 0 {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault == terminalFaultRestrictSelf || rawLandlockRestrictSelf(preparedPtr.rulesetFD, 0) != 0 {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault == terminalFaultRulesetClose || rawCloseFD(preparedPtr.rulesetFD) != 0 {
		exitGroup(runtimeFailureExitCode)
	}
	currentTID, errno := rawGetTID()
	if errno != 0 || currentTID != lockedTID || preparedPtr.fault == terminalFaultTIDMismatch {
		exitGroup(runtimeFailureExitCode)
	}
	if preparedPtr.fault != terminalFaultExecve {
		_, _, _ = unix.RawSyscall(unix.SYS_EXECVE,
			uintptr(unsafe.Pointer(&preparedPtr.pathStorage[0])),
			uintptr(unsafe.Pointer(&preparedPtr.argv[0])),
			uintptr(unsafe.Pointer(&preparedPtr.envp[0])))
	}
	runtime.KeepAlive(preparedPtr)
	exitGroup(executionFailureExitCode)
	for {
	}
}

//go:nosplit
func rawGetTID() (uintptr, unix.Errno) {
	tid, _, errno := unix.RawSyscall(unix.SYS_GETTID, 0, 0, 0)
	return tid, errno
}

//go:nosplit
func rawNoNewPrivs() unix.Errno {
	_, _, errno := unix.RawSyscall6(unix.SYS_PRCTL, uintptr(unix.PR_SET_NO_NEW_PRIVS), 1, 0, 0, 0, 0)
	return errno
}

//go:nosplit
func rawLandlockRestrictSelf(rulesetFD int, flags uint32) unix.Errno {
	_, _, errno := unix.RawSyscall(unix.SYS_LANDLOCK_RESTRICT_SELF, uintptr(rulesetFD), uintptr(flags), 0)
	return errno
}

//go:nosplit
func rawCloseFD(fd int) unix.Errno {
	_, _, errno := unix.RawSyscall(unix.SYS_CLOSE, uintptr(fd), 0, 0)
	return errno
}

//go:nosplit
func exitGroup(code int) {
	for {
		_, _, _ = unix.RawSyscall(unix.SYS_EXIT_GROUP, uintptr(code), 0, 0)
	}
}
