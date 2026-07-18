package sandbox

import (
	llsyscall "github.com/landlock-lsm/go-landlock/landlock/syscall"
	"golang.org/x/sys/unix"
)

type prepareV3Ops struct {
	getABI        func() (int, error)
	createRuleset func(*llsyscall.RulesetAttr, int) (int, error)
	openPath      func(string, int, uint32) (int, error)
	fstat         func(int, *unix.Stat_t) error
	addPathRule   func(int, *llsyscall.PathBeneathAttr, int) error
	setCLOEXEC    func(int) error
	getCLOEXEC    func(int) (bool, error)
	closeFD       func(int) error
}

var productionPrepareV3Ops = prepareV3Ops{
	getABI:        llsyscall.LandlockGetABIVersion,
	createRuleset: llsyscall.LandlockCreateRuleset,
	openPath:      unix.Open,
	fstat:         unix.Fstat,
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
