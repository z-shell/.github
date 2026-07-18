// Package sandbox provides the fail-closed child boundary used by renderers.
package sandbox

import (
	"errors"
	"fmt"
	"sort"
	"strings"

	llsyscall "github.com/landlock-lsm/go-landlock/landlock/syscall"
	"golang.org/x/sys/unix"
)

const (
	runtimeFailureExitCode   = 4
	executionFailureExitCode = 5

	exactV3HandledAccess uint64 = llsyscall.AccessFSExecute |
		llsyscall.AccessFSWriteFile |
		llsyscall.AccessFSReadFile |
		llsyscall.AccessFSReadDir |
		llsyscall.AccessFSRemoveDir |
		llsyscall.AccessFSRemoveFile |
		llsyscall.AccessFSMakeChar |
		llsyscall.AccessFSMakeDir |
		llsyscall.AccessFSMakeReg |
		llsyscall.AccessFSMakeSock |
		llsyscall.AccessFSMakeFifo |
		llsyscall.AccessFSMakeBlock |
		llsyscall.AccessFSMakeSym |
		llsyscall.AccessFSRefer |
		llsyscall.AccessFSTruncate

	readOnlyV3Access = llsyscall.AccessFSExecute |
		llsyscall.AccessFSReadFile |
		llsyscall.AccessFSReadDir
	readWriteV3Access  = exactV3HandledAccess &^ llsyscall.AccessFSRefer
	nullDeviceV3Access = llsyscall.AccessFSExecute |
		llsyscall.AccessFSWriteFile |
		llsyscall.AccessFSReadFile |
		llsyscall.AccessFSTruncate
)

var (
	// ErrLandlockV3Unavailable means the exact required ABI could not be applied.
	ErrLandlockV3Unavailable = errors.New("Landlock V3 unavailable")
	// ErrDescriptorClose means inherited descriptors could not be closed.
	ErrDescriptorClose = errors.New("inherited descriptor close failed")
	// ErrRestrictedExec means the restricted target could not be executed.
	ErrRestrictedExec = errors.New("restricted exec failed")
)

// Policy is the exact filesystem view inherited by a restricted target.
type Policy struct {
	ReadOnlyPaths  []string
	ReadWritePaths []string
}

// ExecSpec describes a target that replaces the current, already-isolated child.
type ExecSpec struct {
	Path   string
	Args   []string
	Env    []string
	Policy Policy
}

type preparedV3 struct {
	rulesetFD int
}

func prepareV3(policy Policy) (preparedV3, error) {
	return prepareV3WithOps(policy, productionPrepareV3Ops)
}

func prepareV3WithOps(policy Policy, ops prepareV3Ops) (preparedV3, error) {
	if ops.getABI == nil || ops.createRuleset == nil || ops.openPath == nil || ops.fstat == nil ||
		ops.addPathRule == nil || ops.setCLOEXEC == nil || ops.getCLOEXEC == nil || ops.closeFD == nil {
		return preparedV3{}, fmt.Errorf("%w: incomplete ruleset operations", ErrLandlockV3Unavailable)
	}
	abi, err := ops.getABI()
	if err != nil || abi < 3 {
		return preparedV3{}, ErrLandlockV3Unavailable
	}

	readOnly, readWrite, err := validatePolicy(policy)
	if err != nil {
		return preparedV3{}, err
	}
	attribute := llsyscall.RulesetAttr{
		HandledAccessFS:  exactV3HandledAccess,
		HandledAccessNet: 0,
		Scoped:           0,
	}
	rulesetFD, err := ops.createRuleset(&attribute, 0)
	if err != nil {
		return preparedV3{}, fmt.Errorf("%w: create ruleset", ErrLandlockV3Unavailable)
	}
	if rulesetFD < 3 || uint64(rulesetFD) >= uint64(^uint32(0)) {
		if rulesetFD >= 0 {
			_ = ops.closeFD(rulesetFD)
		}
		return preparedV3{}, fmt.Errorf("%w: invalid ruleset descriptor", ErrLandlockV3Unavailable)
	}
	fail := func(cause error) (preparedV3, error) {
		_ = ops.closeFD(rulesetFD)
		return preparedV3{}, cause
	}

	type ruleSource struct {
		path      string
		access    uint64
		directory bool
	}
	sources := make([]ruleSource, 0, len(readOnly)+len(readWrite)+1)
	for _, path := range readOnly {
		sources = append(sources, ruleSource{path: path, access: readOnlyV3Access, directory: true})
	}
	for _, path := range readWrite {
		sources = append(sources, ruleSource{path: path, access: readWriteV3Access, directory: true})
	}
	sources = append(sources, ruleSource{path: "/dev/null", access: nullDeviceV3Access})

	for _, source := range sources {
		fd, openErr := ops.openPath(source.path, unix.O_PATH|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
		if openErr != nil {
			return fail(fmt.Errorf("%w: open rule source", ErrLandlockV3Unavailable))
		}
		var stat unix.Stat_t
		if statErr := ops.fstat(fd, &stat); statErr != nil {
			_ = ops.closeFD(fd)
			return fail(fmt.Errorf("%w: inspect opened rule source", ErrLandlockV3Unavailable))
		}
		if source.directory {
			if stat.Mode&unix.S_IFMT != unix.S_IFDIR {
				_ = ops.closeFD(fd)
				return fail(fmt.Errorf("%w: rule source is not a directory", ErrLandlockV3Unavailable))
			}
		} else if stat.Mode&unix.S_IFMT != unix.S_IFCHR ||
			unix.Major(uint64(stat.Rdev)) != 1 || unix.Minor(uint64(stat.Rdev)) != 3 {
			_ = ops.closeFD(fd)
			return fail(fmt.Errorf("%w: null device identity mismatch", ErrLandlockV3Unavailable))
		}
		pathAttribute := llsyscall.PathBeneathAttr{AllowedAccess: source.access, ParentFd: fd}
		if addErr := ops.addPathRule(rulesetFD, &pathAttribute, 0); addErr != nil {
			_ = ops.closeFD(fd)
			return fail(fmt.Errorf("%w: add path rule", ErrLandlockV3Unavailable))
		}
		if closeErr := ops.closeFD(fd); closeErr != nil {
			return fail(fmt.Errorf("%w: close rule source", ErrLandlockV3Unavailable))
		}
	}

	if err := ops.setCLOEXEC(rulesetFD); err != nil {
		return fail(fmt.Errorf("%w: set ruleset CLOEXEC", ErrLandlockV3Unavailable))
	}
	cloexec, err := ops.getCLOEXEC(rulesetFD)
	if err != nil || !cloexec {
		return fail(fmt.Errorf("%w: verify ruleset CLOEXEC", ErrLandlockV3Unavailable))
	}
	return preparedV3{rulesetFD: rulesetFD}, nil
}

func validatePolicy(policy Policy) ([]string, []string, error) {
	seen := make(map[string]struct{}, len(policy.ReadOnlyPaths)+len(policy.ReadWritePaths))
	validate := func(paths []string) ([]string, error) {
		validated := append([]string(nil), paths...)
		for _, path := range validated {
			if path == "" || strings.ContainsRune(path, 0) || !strings.HasPrefix(path, "/") ||
				(path != "/" && path != strings.TrimSuffix(path, "/")) {
				return nil, fmt.Errorf("%w: invalid rule path", ErrLandlockV3Unavailable)
			}
			if _, duplicate := seen[path]; duplicate {
				return nil, fmt.Errorf("%w: duplicate rule path", ErrLandlockV3Unavailable)
			}
			seen[path] = struct{}{}
		}
		sort.Strings(validated)
		return validated, nil
	}
	readOnly, err := validate(policy.ReadOnlyPaths)
	if err != nil {
		return nil, nil, err
	}
	readWrite, err := validate(policy.ReadWritePaths)
	if err != nil {
		return nil, nil, err
	}
	return readOnly, readWrite, nil
}
