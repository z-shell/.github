package sandbox

import (
	"context"
	"errors"
	"fmt"
	"io"
	"os/exec"
	"syscall"
	"time"

	"golang.org/x/sys/unix"
)

const defaultTimeout = 45 * time.Second

// ErrProcessTimeout means the complete child process group exceeded its limit.
var ErrProcessTimeout = errors.New("restricted child timed out")

// Child describes a hidden restricted child process.
type Child struct {
	Path    string
	Args    []string
	Env     []string
	Dir     string
	Stdin   io.Reader
	Stdout  io.Writer
	Stderr  io.Writer
	Timeout time.Duration
}

// Outcome preserves the direct child's wait status without conflating normal
// reserved exit codes with signals that happen to use the same numbers.
type Outcome struct {
	Exited   bool
	ExitCode int
	Signaled bool
	Signal   unix.Signal
	TimedOut bool
}

// RunRestrictedChild starts one process group, observes the direct child
// without reaping it, attempts group cleanup after every outcome, and then
// performs the one direct-child wait that reaps it.
func RunRestrictedChild(ctx context.Context, child Child) (Outcome, error) {
	timeout := child.Timeout
	if timeout == 0 {
		timeout = defaultTimeout
	}
	deadline, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	command := exec.Command(child.Path, child.Args...)
	command.Env = child.Env
	command.Dir = child.Dir
	command.Stdin = child.Stdin
	command.Stdout = child.Stdout
	command.Stderr = child.Stderr
	command.WaitDelay = 2 * time.Second
	command.SysProcAttr = &syscall.SysProcAttr{
		Setpgid:   true,
		Pdeathsig: syscall.SIGKILL,
	}
	if err := command.Start(); err != nil {
		return Outcome{}, fmt.Errorf("start restricted child: %w", err)
	}

	observed := make(chan error, 1)
	go func() {
		var info unix.Siginfo
		observed <- unix.Waitid(unix.P_PID, command.Process.Pid, &info, unix.WEXITED|unix.WNOWAIT, nil)
	}()

	timedOut := false
	contextErr := error(nil)
	observeErr := error(nil)
	select {
	case observeErr = <-observed:
	case <-deadline.Done():
		if ctx.Err() != nil {
			contextErr = ctx.Err()
		} else if errors.Is(deadline.Err(), context.DeadlineExceeded) {
			timedOut = true
		} else {
			contextErr = deadline.Err()
		}
		_ = unix.Kill(-command.Process.Pid, unix.SIGKILL)
		observeErr = <-observed
	}

	killErr := unix.Kill(-command.Process.Pid, unix.SIGKILL)
	waitErr := command.Wait()
	if timedOut {
		return Outcome{TimedOut: true}, ErrProcessTimeout
	}
	outcome := outcomeFromCommand(command)
	if contextErr != nil {
		return outcome, contextErr
	}
	if observeErr != nil {
		return outcome, fmt.Errorf("observe restricted child: %w", observeErr)
	}
	if killErr != nil && !errors.Is(killErr, unix.ESRCH) {
		return outcome, fmt.Errorf("clean restricted child group: %w", killErr)
	}
	var exitError *exec.ExitError
	if waitErr != nil && !errors.As(waitErr, &exitError) {
		return outcome, fmt.Errorf("wait restricted child: %w", waitErr)
	}
	return outcome, nil
}

func outcomeFromCommand(command *exec.Cmd) Outcome {
	if command.ProcessState == nil {
		return Outcome{}
	}
	waitStatus, ok := command.ProcessState.Sys().(syscall.WaitStatus)
	if !ok {
		return Outcome{}
	}
	if waitStatus.Exited() {
		return Outcome{Exited: true, ExitCode: waitStatus.ExitStatus()}
	}
	if waitStatus.Signaled() {
		return Outcome{Signaled: true, Signal: unix.Signal(waitStatus.Signal())}
	}
	return Outcome{}
}
