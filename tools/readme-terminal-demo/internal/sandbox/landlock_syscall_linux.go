package sandbox

import (
	llsyscall "github.com/landlock-lsm/go-landlock/landlock/syscall"
	"golang.org/x/sys/unix"
)

type prepareV3Ops struct {
	getABI        func() (int, error)
	createRuleset func(*llsyscall.RulesetAttr, int) (int, error)
	openPath      func(string, int, uint32) (int, error)
	openPathAt    func(int, string, int, uint32) (int, error)
	fstat         func(int, *unix.Stat_t) error
	fstatAt       func(int, string, *unix.Stat_t, int) error
	fstatfs       func(int, *unix.Statfs_t) error
	readDirNames  func(int) ([]string, error)
	addPathRule   func(int, *llsyscall.PathBeneathAttr, int) error
	setCLOEXEC    func(int) error
	getCLOEXEC    func(int) (bool, error)
	closeFD       func(int) error
}

var productionPrepareV3Ops = prepareV3Ops{
	getABI:        llsyscall.LandlockGetABIVersion,
	createRuleset: llsyscall.LandlockCreateRuleset,
	openPath:      openRulePath,
	openPathAt:    unix.Openat,
	fstat:         unix.Fstat,
	fstatAt:       unix.Fstatat,
	fstatfs:       unix.Fstatfs,
	readDirNames:  readDirectoryNames,
	addPathRule:   llsyscall.LandlockAddPathBeneathRule,
	setCLOEXEC: func(fd int) error {
		_, err := unix.FcntlInt(uintptr(fd), unix.F_SETFD, unix.FD_CLOEXEC)
		return err
	},
	getCLOEXEC: func(fd int) (bool, error) {
		flags, err := unix.FcntlInt(uintptr(fd), unix.F_GETFD, 0)
		return flags&unix.FD_CLOEXEC != 0, err
	},
	closeFD: unix.Close,
}

func openRulePath(path string, flags int, mode uint32) (int, error) {
	return unix.Openat2(unix.AT_FDCWD, path, &unix.OpenHow{
		Flags:   uint64(flags),
		Mode:    uint64(mode),
		Resolve: unix.RESOLVE_NO_SYMLINKS | unix.RESOLVE_NO_MAGICLINKS,
	})
}

func readDirectoryNames(fd int) ([]string, error) {
	buffer := make([]byte, 4096)
	names := make([]string, 0, 2)
	for {
		count, err := unix.ReadDirent(fd, buffer)
		if err != nil {
			return nil, err
		}
		if count == 0 {
			return names, nil
		}
		consumed, _, batch := unix.ParseDirent(buffer[:count], -1, nil)
		if consumed != count {
			return nil, unix.EIO
		}
		for _, name := range batch {
			if name == "." || name == ".." {
				continue
			}
			names = append(names, name)
			if len(names) > 1 {
				return names, nil
			}
		}
	}
}
