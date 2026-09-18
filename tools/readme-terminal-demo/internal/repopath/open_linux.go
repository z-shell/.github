//go:build linux

package repopath

import (
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"strconv"
	"sync"
	"sync/atomic"

	"golang.org/x/sys/unix"
)

// resolveFlags is the kernel-enforced containment contract.
//
//	RESOLVE_BENEATH       the resolution may not escape the root descriptor
//	RESOLVE_NO_SYMLINKS   no component may be a symlink
//	RESOLVE_NO_MAGICLINKS no component may be a /proc style magic link
//
// A rejected resolution surfaces as EXDEV, ELOOP, or EAGAIN depending on which
// guard fires; all of them map to the same sanitized class.
const resolveFlags = unix.RESOLVE_BENEATH | unix.RESOLVE_NO_SYMLINKS | unix.RESOLVE_NO_MAGICLINKS

// Root is an open repository root that constrains every relative open beneath
// itself.
//
// The root descriptor is private and every child acquisition holds the read
// side of mu while it uses that descriptor, so Close cannot release it, and
// the kernel cannot reuse its number, between the closed check and the
// openat2 or dup that depends on it.
type Root struct {
	mu     sync.RWMutex
	fd     int
	closed bool

	// replaceMu serializes AtomicReplace calls on this root, so the identity
	// check after promotion can only ever see a foreign entry, never the
	// staging file of a concurrent call through the same root.
	replaceMu sync.Mutex
	// temporaries names staging files so a failed AtomicReplace can clean up.
	temporaries atomic.Uint64
}

// testBeforeStagingCheck and testBeforePromote are test-only seams that let a
// test interleave a hostile directory change at the two points AtomicReplace
// verifies the staging entry. Production code never sets them.
var (
	testBeforeStagingCheck func(parent int, staging string)
	testBeforePromote      func(parent int, staging string)
)

// OpenRoot opens path as a containment root. The root itself is trusted input
// supplied by the renderer, not by the repository under test.
func OpenRoot(path string) (*Root, error) {
	if path == "" {
		return nil, unsafePath("root", errors.New("root path is required"))
	}

	fd, err := unix.Open(path, unix.O_RDONLY|unix.O_DIRECTORY|unix.O_CLOEXEC|unix.O_NOFOLLOW, 0)
	if err != nil {
		return nil, unsafePath("root", fmt.Errorf("open root: %w", err))
	}

	var stat unix.Stat_t
	if err := unix.Fstat(fd, &stat); err != nil {
		_ = unix.Close(fd)
		return nil, unsafePath("root", fmt.Errorf("inspect root: %w", err))
	}
	if stat.Mode&unix.S_IFMT != unix.S_IFDIR {
		_ = unix.Close(fd)
		return nil, unsafePath("root", errors.New("root is not a directory"))
	}

	return &Root{fd: fd}, nil
}

// Close releases the root descriptor. It is safe to call more than once, and
// it waits for every in-flight child acquisition before the descriptor goes
// away.
func (r *Root) Close() error {
	if r == nil {
		return nil
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.closed {
		return nil
	}
	r.closed = true
	fd := r.fd
	r.fd = -1
	if err := unix.Close(fd); err != nil {
		return unsafePath("root", fmt.Errorf("close root: %w", err))
	}
	return nil
}

// openAt performs the kernel-enforced resolution shared by every accessor.
//
// The open is non-blocking so a repository-controlled FIFO cannot stall the
// renderer waiting for a writer, and the opened descriptor is inspected before
// it is handed out: only a regular file or a directory is accepted. The flag is
// cleared again afterwards so the returned descriptor reads normally.
func (r *Root) openAt(rel string, flags uint64) (int, error) {
	if r == nil {
		return -1, unsafePath("root", errors.New("root is nil"))
	}
	if err := validateRelative(rel); err != nil {
		return -1, err
	}

	how := unix.OpenHow{
		Flags:   flags | unix.O_CLOEXEC | unix.O_NOFOLLOW | unix.O_NONBLOCK,
		Resolve: resolveFlags,
	}
	r.mu.RLock()
	if r.closed {
		r.mu.RUnlock()
		return -1, unsafePath("root", errors.New("root is closed"))
	}
	fd, err := unix.Openat2(r.fd, rel, &how)
	r.mu.RUnlock()
	if err != nil {
		return -1, unsafePath("path", fmt.Errorf("resolve path: %w", err))
	}

	var stat unix.Stat_t
	if err := unix.Fstat(fd, &stat); err != nil {
		_ = unix.Close(fd)
		return -1, unsafePath("path", fmt.Errorf("inspect path: %w", err))
	}
	switch stat.Mode & unix.S_IFMT {
	case unix.S_IFREG, unix.S_IFDIR:
	default:
		_ = unix.Close(fd)
		return -1, unsafePath("path", errors.New("path is not a regular file or directory"))
	}

	status, err := unix.FcntlInt(uintptr(fd), unix.F_GETFL, 0)
	if err == nil {
		_, err = unix.FcntlInt(uintptr(fd), unix.F_SETFL, status&^unix.O_NONBLOCK)
	}
	if err != nil {
		_ = unix.Close(fd)
		return -1, unsafePath("path", fmt.Errorf("restore blocking mode: %w", err))
	}
	return fd, nil
}

// OpenRead opens a repository path for reading.
//
// A directory is permitted: manifest loading opens the declared fixtures
// directory through this same boundary and inspects its type afterwards.
func (r *Root) OpenRead(rel string) (*os.File, error) {
	fd, err := r.openAt(rel, unix.O_RDONLY)
	if err != nil {
		return nil, err
	}
	return os.NewFile(uintptr(fd), rel), nil
}

// OpenDir opens a repository path that must be a directory.
func (r *Root) OpenDir(rel string) (*os.File, error) {
	fd, err := r.openAt(rel, unix.O_RDONLY|unix.O_DIRECTORY)
	if err != nil {
		return nil, err
	}
	return os.NewFile(uintptr(fd), rel), nil
}

// AtomicReplace writes src to rel through a staging file inside the same
// directory, then renames it into place.
//
// A destination that already exists as anything but a regular file, including
// a pre-planted symlink, is rejected before any staging file is created; it is
// never followed and never replaced. The staging file itself is created with
// O_EXCL beneath the contained parent, so nothing can redirect the write.
//
// O_EXCL protects creation only. A writer to the same directory could still
// swap the staging name for another entry between creation and promotion, so
// the staging entry's identity (device and inode of the descriptor that was
// written) is verified immediately before the rename and the promoted
// destination is verified immediately after it. A mismatch is reported as a
// containment failure and the foreign entry is unlinked; the method never
// returns success for a promotion it did not write. Calls through the same
// root are serialized, so two replacements of one destination cannot
// interleave and mistake each other for that foreign entry.
func (r *Root) AtomicReplace(rel string, src io.Reader, mode fs.FileMode) error {
	if src == nil {
		return unsafePath("path", errors.New("source reader is required"))
	}
	if err := validateRelative(rel); err != nil {
		return err
	}
	if r == nil {
		return unsafePath("root", errors.New("root is nil"))
	}
	r.replaceMu.Lock()
	defer r.replaceMu.Unlock()

	parent, name, err := r.openParent(rel)
	if err != nil {
		return err
	}
	defer unix.Close(parent)

	// Reject a destination that already exists as anything but a regular file,
	// so a symlink or device can never be silently replaced or followed.
	var existing unix.Stat_t
	switch err := unix.Fstatat(parent, name, &existing, unix.AT_SYMLINK_NOFOLLOW); {
	case err == nil:
		if existing.Mode&unix.S_IFMT != unix.S_IFREG {
			return unsafePath("path", errors.New("destination is not a regular file"))
		}
	case errors.Is(err, unix.ENOENT):
		// A new file is fine.
	default:
		return unsafePath("path", fmt.Errorf("inspect destination: %w", err))
	}

	staging := ".readme-terminal-demo." + strconv.FormatUint(r.temporaries.Add(1), 10) + ".tmp"
	stagingFD, err := unix.Openat(
		parent, staging,
		unix.O_WRONLY|unix.O_CREAT|unix.O_EXCL|unix.O_CLOEXEC|unix.O_NOFOLLOW,
		uint32(mode.Perm()),
	)
	if err != nil {
		return unsafePath("path", fmt.Errorf("create staging file: %w", err))
	}

	cleanup := func() {
		_ = unix.Unlinkat(parent, staging, 0)
	}

	var written unix.Stat_t
	if err := unix.Fstat(stagingFD, &written); err != nil {
		_ = unix.Close(stagingFD)
		cleanup()
		return unsafePath("path", fmt.Errorf("inspect staging file: %w", err))
	}

	file := os.NewFile(uintptr(stagingFD), staging)
	if _, err := io.Copy(file, src); err != nil {
		_ = file.Close()
		cleanup()
		return unsafePath("path", fmt.Errorf("write staging file: %w", err))
	}
	// The mode is set explicitly because the open mode is masked by umask.
	if err := file.Chmod(mode.Perm()); err != nil {
		_ = file.Close()
		cleanup()
		return unsafePath("path", fmt.Errorf("set staging mode: %w", err))
	}
	if err := file.Sync(); err != nil {
		_ = file.Close()
		cleanup()
		return unsafePath("path", fmt.Errorf("sync staging file: %w", err))
	}
	if err := file.Close(); err != nil {
		cleanup()
		return unsafePath("path", fmt.Errorf("close staging file: %w", err))
	}

	if testBeforeStagingCheck != nil {
		testBeforeStagingCheck(parent, staging)
	}
	if err := verifyIdentity(parent, staging, &written); err != nil {
		cleanup()
		return unsafePath("path", fmt.Errorf("staging entry: %w", err))
	}
	if testBeforePromote != nil {
		testBeforePromote(parent, staging)
	}
	if err := unix.Renameat(parent, staging, parent, name); err != nil {
		cleanup()
		return unsafePath("path", fmt.Errorf("promote staging file: %w", err))
	}
	if err := verifyIdentity(parent, name, &written); err != nil {
		// The promoted entry is not the file this call wrote. Remove it so a
		// foreign entry never survives at the destination under a success or
		// failure return.
		_ = unix.Unlinkat(parent, name, 0)
		return unsafePath("path", fmt.Errorf("promoted entry: %w", err))
	}
	return nil
}

// verifyIdentity proves that name inside parent, resolved without following a
// final symlink, is exactly the file described by want.
func verifyIdentity(parent int, name string, want *unix.Stat_t) error {
	var got unix.Stat_t
	if err := unix.Fstatat(parent, name, &got, unix.AT_SYMLINK_NOFOLLOW); err != nil {
		return fmt.Errorf("inspect: %w", err)
	}
	if got.Dev != want.Dev || got.Ino != want.Ino {
		return errors.New("entry was replaced")
	}
	return nil
}

// openParent resolves the contained parent directory of rel and returns it with
// the final component name. The final component is never resolved here, so the
// caller decides how to treat it.
func (r *Root) openParent(rel string) (int, string, error) {
	if r == nil {
		return -1, "", unsafePath("root", errors.New("root is nil"))
	}

	name := rel
	parentRel := ""
	if index := lastSlash(rel); index >= 0 {
		parentRel = rel[:index]
		name = rel[index+1:]
	}
	if name == "" || name == "." || name == ".." {
		return -1, "", unsafePath("path", errors.New("path has no usable final component"))
	}

	if parentRel == "" {
		r.mu.RLock()
		if r.closed {
			r.mu.RUnlock()
			return -1, "", unsafePath("root", errors.New("root is closed"))
		}
		fd, err := unix.FcntlInt(uintptr(r.fd), unix.F_DUPFD_CLOEXEC, 0)
		r.mu.RUnlock()
		if err != nil {
			return -1, "", unsafePath("root", fmt.Errorf("duplicate root: %w", err))
		}
		return fd, name, nil
	}

	fd, err := r.openAt(parentRel, unix.O_RDONLY|unix.O_DIRECTORY)
	if err != nil {
		return -1, "", err
	}
	return fd, name, nil
}

func lastSlash(value string) int {
	for i := len(value) - 1; i >= 0; i-- {
		if value[i] == '/' {
			return i
		}
	}
	return -1
}
