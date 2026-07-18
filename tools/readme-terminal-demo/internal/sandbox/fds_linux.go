package sandbox

import "golang.org/x/sys/unix"

type rawCloseRange func(first, last, flags uint32) unix.Errno

//go:nosplit
func rawCloseRangeCall(first, last, flags uint32) unix.Errno {
	_, _, errno := unix.RawSyscall(unix.SYS_CLOSE_RANGE, uintptr(first), uintptr(last), uintptr(flags))
	return errno
}

func closeInheritedExcept(rulesetFD int) unix.Errno {
	if errno := rawCloseRangeCall(uint32(rulesetFD+1), ^uint32(0), unix.CLOSE_RANGE_UNSHARE); errno != 0 {
		return errno
	}
	if rulesetFD > 3 {
		return rawCloseRangeCall(3, uint32(rulesetFD-1), 0)
	}
	return 0
}

func closeInheritedExceptWith(rulesetFD int, call rawCloseRange) unix.Errno {
	if errno := call(uint32(rulesetFD+1), ^uint32(0), unix.CLOSE_RANGE_UNSHARE); errno != 0 {
		return errno
	}
	if rulesetFD > 3 {
		return call(3, uint32(rulesetFD-1), 0)
	}
	return 0
}
