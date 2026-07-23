// Package sandbox provides the fail-closed child boundary used by renderers.
package sandbox

import (
	"errors"
	"fmt"
	"path/filepath"
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
	privateDevptsPTYV3Access = llsyscall.AccessFSWriteFile
	devptsSuperMagic         = 0x1cd1
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
	// AllowPrivateDevptsPTY grants only WRITE_FILE beneath a verified private
	// /dev/pts mount. The preflight requires a devpts filesystem whose initial
	// topology is exactly ptmx and validates that device as 5:2 through the
	// opened directory. Landlock ABI 3 mediates path access, not device ioctls;
	// this field does not add ioctl, creation, removal, or truncate authority.
	AllowPrivateDevptsPTY bool
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

type privateDevptsPTYSource struct {
	directoryFD   int
	directoryStat unix.Stat_t
	parentStat    unix.Stat_t
	rootStat      unix.Stat_t
}

func prepareV3(policy Policy) (preparedV3, error) {
	return prepareV3WithOps(policy, productionPrepareV3Ops)
}

func prepareV3WithOps(policy Policy, ops prepareV3Ops) (preparedV3, error) {
	if ops.getABI == nil || ops.createRuleset == nil || ops.openPath == nil || ops.fstat == nil ||
		ops.addPathRule == nil || ops.setCLOEXEC == nil || ops.getCLOEXEC == nil || ops.closeFD == nil {
		return preparedV3{}, fmt.Errorf("%w: incomplete ruleset operations", ErrLandlockV3Unavailable)
	}
	if policy.AllowPrivateDevptsPTY &&
		(ops.openPathAt == nil || ops.fstatAt == nil || ops.fstatfs == nil || ops.readDirNames == nil) {
		return preparedV3{}, fmt.Errorf("%w: incomplete private devpts operations", ErrLandlockV3Unavailable)
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

	var privatePTY *privateDevptsPTYSource
	if policy.AllowPrivateDevptsPTY {
		source, prepareErr := preparePrivateDevptsPTYSource(ops)
		if prepareErr != nil {
			return fail(prepareErr)
		}
		privatePTY = &source
	}
	closePrivatePTY := func() error {
		if privatePTY == nil || privatePTY.directoryFD < 0 {
			return nil
		}
		fd := privatePTY.directoryFD
		privatePTY.directoryFD = -1
		return ops.closeFD(fd)
	}
	failWithPrivatePTY := func(cause error) (preparedV3, error) {
		if closeErr := closePrivatePTY(); closeErr != nil {
			cause = errors.Join(cause, fmt.Errorf("%w: close private devpts: %v", ErrLandlockV3Unavailable, closeErr))
		}
		return fail(cause)
	}

	type ruleSource struct {
		path      string
		access    uint64
		directory bool
	}
	sources := make([]ruleSource, 0, len(readOnly)+len(readWrite))
	for _, path := range readOnly {
		sources = append(sources, ruleSource{path: path, access: readOnlyV3Access, directory: true})
	}
	for _, path := range readWrite {
		sources = append(sources, ruleSource{path: path, access: readWriteV3Access, directory: true})
	}
	addRuleSource := func(source ruleSource) error {
		fd, openErr := ops.openPath(source.path, unix.O_PATH|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
		if openErr != nil {
			return fmt.Errorf("%w: open rule source", ErrLandlockV3Unavailable)
		}
		var stat unix.Stat_t
		if statErr := ops.fstat(fd, &stat); statErr != nil {
			_ = ops.closeFD(fd)
			return fmt.Errorf("%w: inspect opened rule source", ErrLandlockV3Unavailable)
		}
		if source.access == readWriteV3Access && overlapsPrivateDevptsPTY(stat, privatePTY) {
			_ = ops.closeFD(fd)
			return fmt.Errorf("%w: writable rule aliases private devpts boundary", ErrLandlockV3Unavailable)
		}
		if source.directory {
			if stat.Mode&unix.S_IFMT != unix.S_IFDIR {
				_ = ops.closeFD(fd)
				return fmt.Errorf("%w: rule source is not a directory", ErrLandlockV3Unavailable)
			}
		} else if stat.Mode&unix.S_IFMT != unix.S_IFCHR ||
			unix.Major(uint64(stat.Rdev)) != 1 || unix.Minor(uint64(stat.Rdev)) != 3 {
			_ = ops.closeFD(fd)
			return fmt.Errorf("%w: null device identity mismatch", ErrLandlockV3Unavailable)
		}
		pathAttribute := llsyscall.PathBeneathAttr{AllowedAccess: source.access, ParentFd: fd}
		if addErr := ops.addPathRule(rulesetFD, &pathAttribute, 0); addErr != nil {
			_ = ops.closeFD(fd)
			return fmt.Errorf("%w: add path rule", ErrLandlockV3Unavailable)
		}
		if closeErr := ops.closeFD(fd); closeErr != nil {
			return fmt.Errorf("%w: close rule source", ErrLandlockV3Unavailable)
		}
		return nil
	}

	for _, source := range sources {
		if err := addRuleSource(source); err != nil {
			return failWithPrivatePTY(err)
		}
	}
	if privatePTY != nil {
		attribute := llsyscall.PathBeneathAttr{
			AllowedAccess: privateDevptsPTYV3Access,
			ParentFd:      privatePTY.directoryFD,
		}
		if err := ops.addPathRule(rulesetFD, &attribute, 0); err != nil {
			return failWithPrivatePTY(fmt.Errorf("%w: add private devpts rule", ErrLandlockV3Unavailable))
		}
		if err := closePrivatePTY(); err != nil {
			return fail(fmt.Errorf("%w: close private devpts", ErrLandlockV3Unavailable))
		}
	}
	if err := addRuleSource(ruleSource{path: "/dev/null", access: nullDeviceV3Access}); err != nil {
		return failWithPrivatePTY(err)
	}

	if err := ops.setCLOEXEC(rulesetFD); err != nil {
		return failWithPrivatePTY(fmt.Errorf("%w: set ruleset CLOEXEC", ErrLandlockV3Unavailable))
	}
	cloexec, err := ops.getCLOEXEC(rulesetFD)
	if err != nil || !cloexec {
		return failWithPrivatePTY(fmt.Errorf("%w: verify ruleset CLOEXEC", ErrLandlockV3Unavailable))
	}
	return preparedV3{rulesetFD: rulesetFD}, nil
}

func overlapsPrivateDevptsPTY(stat unix.Stat_t, privatePTY *privateDevptsPTYSource) bool {
	if privatePTY == nil {
		return false
	}
	return stat.Dev == privatePTY.directoryStat.Dev ||
		sameFileIdentity(stat, privatePTY.parentStat) ||
		sameFileIdentity(stat, privatePTY.rootStat)
}

func sameFileIdentity(left, right unix.Stat_t) bool {
	return left.Dev == right.Dev && left.Ino == right.Ino
}

func preparePrivateDevptsPTYSource(ops prepareV3Ops) (privateDevptsPTYSource, error) {
	directoryFD, err := ops.openPath(
		"/dev/pts",
		unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC|unix.O_NOFOLLOW,
		0,
	)
	if err != nil {
		return privateDevptsPTYSource{}, fmt.Errorf("%w: open private devpts", ErrLandlockV3Unavailable)
	}
	source := privateDevptsPTYSource{directoryFD: directoryFD}
	closeDirectory := func() error {
		if source.directoryFD < 0 {
			return nil
		}
		fd := source.directoryFD
		source.directoryFD = -1
		return ops.closeFD(fd)
	}
	fail := func(cause error) (privateDevptsPTYSource, error) {
		if closeErr := closeDirectory(); closeErr != nil {
			cause = errors.Join(cause, fmt.Errorf("%w: close private devpts: %v", ErrLandlockV3Unavailable, closeErr))
		}
		return privateDevptsPTYSource{}, cause
	}

	if err := ops.fstat(directoryFD, &source.directoryStat); err != nil {
		return fail(fmt.Errorf("%w: inspect private devpts", ErrLandlockV3Unavailable))
	}
	if source.directoryStat.Mode&unix.S_IFMT != unix.S_IFDIR {
		return fail(fmt.Errorf("%w: private devpts is not a directory", ErrLandlockV3Unavailable))
	}
	var filesystemStat unix.Statfs_t
	if err := ops.fstatfs(directoryFD, &filesystemStat); err != nil {
		return fail(fmt.Errorf("%w: inspect private devpts filesystem", ErrLandlockV3Unavailable))
	}
	if filesystemStat.Type != devptsSuperMagic {
		return fail(fmt.Errorf("%w: private devpts filesystem mismatch", ErrLandlockV3Unavailable))
	}
	if err := ops.fstatAt(directoryFD, "..", &source.parentStat, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fail(fmt.Errorf("%w: inspect private devpts parent", ErrLandlockV3Unavailable))
	}
	if source.parentStat.Mode&unix.S_IFMT != unix.S_IFDIR || source.parentStat.Dev == source.directoryStat.Dev {
		return fail(fmt.Errorf("%w: private devpts mount boundary mismatch", ErrLandlockV3Unavailable))
	}
	if err := ops.fstatAt(directoryFD, "../..", &source.rootStat, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fail(fmt.Errorf("%w: inspect private devpts root", ErrLandlockV3Unavailable))
	}
	if source.rootStat.Mode&unix.S_IFMT != unix.S_IFDIR {
		return fail(fmt.Errorf("%w: private devpts root is not a directory", ErrLandlockV3Unavailable))
	}
	names, err := ops.readDirNames(directoryFD)
	if err != nil {
		return fail(fmt.Errorf("%w: inspect private devpts topology", ErrLandlockV3Unavailable))
	}
	if len(names) != 1 || names[0] != "ptmx" {
		return fail(fmt.Errorf("%w: private devpts topology mismatch", ErrLandlockV3Unavailable))
	}

	ptmxFD, err := ops.openPathAt(
		directoryFD,
		"ptmx",
		unix.O_PATH|unix.O_CLOEXEC|unix.O_NOFOLLOW,
		0,
	)
	if err != nil {
		return fail(fmt.Errorf("%w: open private devpts ptmx", ErrLandlockV3Unavailable))
	}
	var ptmxStat unix.Stat_t
	if err := ops.fstat(ptmxFD, &ptmxStat); err != nil {
		_ = ops.closeFD(ptmxFD)
		return fail(fmt.Errorf("%w: inspect private devpts ptmx", ErrLandlockV3Unavailable))
	}
	if ptmxStat.Mode&unix.S_IFMT != unix.S_IFCHR ||
		ptmxStat.Dev != source.directoryStat.Dev ||
		unix.Major(uint64(ptmxStat.Rdev)) != 5 || unix.Minor(uint64(ptmxStat.Rdev)) != 2 {
		_ = ops.closeFD(ptmxFD)
		return fail(fmt.Errorf("%w: private devpts ptmx identity mismatch", ErrLandlockV3Unavailable))
	}
	if err := ops.closeFD(ptmxFD); err != nil {
		return fail(fmt.Errorf("%w: close private devpts ptmx", ErrLandlockV3Unavailable))
	}
	return source, nil
}

func validatePolicy(policy Policy) ([]string, []string, error) {
	seen := make(map[string]struct{}, len(policy.ReadOnlyPaths)+len(policy.ReadWritePaths))
	validate := func(paths []string) ([]string, error) {
		validated := append([]string(nil), paths...)
		for _, path := range validated {
			if path == "" || strings.ContainsRune(path, 0) || !filepath.IsAbs(path) || filepath.Clean(path) != path ||
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
	if policy.AllowPrivateDevptsPTY {
		if _, overlap := seen["/dev/pts"]; overlap {
			return nil, nil, fmt.Errorf("%w: private devpts overlaps a generic rule", ErrLandlockV3Unavailable)
		}
		for _, path := range readWrite {
			if path == "/" || strings.HasPrefix("/dev/pts", path+"/") || strings.HasPrefix(path, "/dev/pts/") {
				return nil, nil, fmt.Errorf("%w: private devpts overlaps a writable rule", ErrLandlockV3Unavailable)
			}
		}
	}
	return readOnly, readWrite, nil
}
