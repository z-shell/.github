//go:build linux

package repopath

import (
	"errors"
	"fmt"
	"io"
	"io/fs"
	"os"
	"strconv"
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
type Root struct {
	Path string
	FD   int

	closed atomic.Bool
	// temporaries names staging files so a failed AtomicReplace can clean up.
	temporaries atomic.Uint64
}

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

	return &Root{Path: path, FD: fd}, nil
}

// Close releases the root descriptor. It is safe to call more than once.
func (r *Root) Close() error {
	if r == nil {
		return nil
	}
	if !r.closed.CompareAndSwap(false, true) {
		return nil
	}
	if err := unix.Close(r.FD); err != nil {
		return unsafePath("root", fmt.Errorf("close root: %w", err))
	}
	return nil
}

// openAt performs the kernel-enforced resolution shared by every accessor.
func (r *Root) openAt(rel string, flags uint64) (int, error) {
	if r == nil {
		return -1, unsafePath("root", errors.New("root is nil"))
	}
	if r.closed.Load() {
		return -1, unsafePath("root", errors.New("root is closed"))
	}
	if err := validateRelative(rel); err != nil {
		return -1, err
	}

	how := unix.OpenHow{
		Flags:   flags | unix.O_CLOEXEC | unix.O_NOFOLLOW,
		Resolve: resolveFlags,
	}
	fd, err := unix.Openat2(r.FD, rel, &how)
	if err != nil {
		return -1, unsafePath("path", fmt.Errorf("resolve path: %w", err))
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
// The staging file is created with O_EXCL beneath the contained parent, so a
// pre-planted symlink at the destination cannot redirect the write: the rename
// replaces the symlink itself rather than following it.
func (r *Root) AtomicReplace(rel string, src io.Reader, mode fs.FileMode) error {
	if src == nil {
		return unsafePath("path", errors.New("source reader is required"))
	}
	if err := validateRelative(rel); err != nil {
		return err
	}

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

	if err := unix.Renameat(parent, staging, parent, name); err != nil {
		cleanup()
		return unsafePath("path", fmt.Errorf("promote staging file: %w", err))
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
	if r.closed.Load() {
		return -1, "", unsafePath("root", errors.New("root is closed"))
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
		fd, err := unix.Dup(r.FD)
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
