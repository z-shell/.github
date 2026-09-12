package repopath

import (
	"bytes"
	"errors"
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/manifest"
)

// assertUnsafePath proves a containment rejection uses the stable sanitized
// contract and never leaks the offending path through the public error string.
func assertUnsafePath(t *testing.T, err error, secrets ...string) {
	t.Helper()
	if err == nil {
		t.Fatal("expected a containment failure, got nil")
	}
	if got := failure.Classify(err); got != failure.UnsafePath {
		t.Errorf("class = %q, want %q", got, failure.UnsafePath)
	}
	if got := failure.ExitCode(err); got != 3 {
		t.Errorf("exit code = %d, want 3", got)
	}
	var structured *failure.Error
	if !errors.As(err, &structured) {
		t.Fatalf("error is not a *failure.Error: %v", err)
	}
	if structured.Stage != failure.StageSource {
		t.Errorf("stage = %q, want %q", structured.Stage, failure.StageSource)
	}
	message := err.Error()
	for _, secret := range secrets {
		// Very short inputs such as "." occur incidentally in the stable
		// error format, so only substantial paths are leak-checked.
		if len(secret) < 4 {
			continue
		}
		if strings.Contains(message, secret) {
			t.Errorf("error message %q leaks path %q", message, secret)
		}
		if strings.Contains(structured.Field, secret) {
			t.Errorf("error field %q leaks path %q", structured.Field, secret)
		}
	}
}

// newRoot builds a populated temporary repository root.
func newRoot(t *testing.T) (*Root, string) {
	t.Helper()
	dir := t.TempDir()

	mustWrite(t, filepath.Join(dir, "manifest.yml"), "version: 1\n")
	if err := os.MkdirAll(filepath.Join(dir, "nested", "deep"), 0o755); err != nil {
		t.Fatalf("create nested directories: %v", err)
	}
	mustWrite(t, filepath.Join(dir, "nested", "deep", "file.txt"), "contents\n")

	root, err := OpenRoot(dir)
	if err != nil {
		t.Fatalf("OpenRoot: %v", err)
	}
	t.Cleanup(func() { _ = root.Close() })
	return root, dir
}

func mustWrite(t *testing.T, path, content string) {
	t.Helper()
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", path, err)
	}
}

func TestOpenReadAcceptsOrdinaryFile(t *testing.T) {
	root, _ := newRoot(t)

	file, err := root.OpenRead("manifest.yml")
	if err != nil {
		t.Fatalf("OpenRead returned an unexpected error: %v", err)
	}
	defer file.Close()

	data, err := io.ReadAll(file)
	if err != nil {
		t.Fatalf("read: %v", err)
	}
	if string(data) != "version: 1\n" {
		t.Errorf("contents = %q, want %q", data, "version: 1\n")
	}
}

func TestOpenReadAcceptsNestedFile(t *testing.T) {
	root, _ := newRoot(t)

	file, err := root.OpenRead("nested/deep/file.txt")
	if err != nil {
		t.Fatalf("OpenRead returned an unexpected error: %v", err)
	}
	defer file.Close()
}

// TestOpenReadAcceptsDirectory pins the seam manifest.Load depends on: it calls
// OpenRead for the fixtures directory and stats it, so OpenRead must open a
// directory rather than requiring a regular file.
func TestOpenReadAcceptsDirectory(t *testing.T) {
	root, _ := newRoot(t)

	file, err := root.OpenRead("nested")
	if err != nil {
		t.Fatalf("OpenRead on a directory returned an unexpected error: %v", err)
	}
	defer file.Close()

	info, err := file.Stat()
	if err != nil {
		t.Fatalf("stat: %v", err)
	}
	if !info.IsDir() {
		t.Error("expected the opened directory to report IsDir")
	}
}

func TestOpenDirRejectsRegularFile(t *testing.T) {
	root, _ := newRoot(t)

	_, err := root.OpenDir("manifest.yml")
	assertUnsafePath(t, err, "manifest.yml")
}

func TestOpenRejectsUnsafePaths(t *testing.T) {
	root, dir := newRoot(t)

	// A symlinked component and a symlinked final component.
	if err := os.Symlink(dir, filepath.Join(dir, "self")); err != nil {
		t.Fatalf("symlink self: %v", err)
	}
	if err := os.Symlink("manifest.yml", filepath.Join(dir, "alias.yml")); err != nil {
		t.Fatalf("symlink alias: %v", err)
	}
	if err := os.Symlink("/etc/passwd", filepath.Join(dir, "absolute-link")); err != nil {
		t.Fatalf("symlink absolute: %v", err)
	}

	cases := []struct {
		name string
		path string
	}{
		{"empty", ""},
		{"absolute", "/etc/passwd"},
		{"dot dot escape", "../outside"},
		{"embedded dot dot", "nested/../../outside"},
		{"trailing dot dot", "nested/.."},
		{"single dot", "./manifest.yml"},
		{"current directory", "."},
		{"double slash", "nested//deep"},
		{"symlinked component", "self/manifest.yml"},
		{"symlinked final component", "alias.yml"},
		{"symlink to absolute path", "absolute-link"},
		{"missing parent", "absent/file.txt"},
		{"missing file", "absent.txt"},
		{"NUL byte", "nested/\x00file"},
		{"backslash escape attempt", "..\\outside"},
	}

	for _, testCase := range cases {
		t.Run(testCase.name, func(t *testing.T) {
			_, err := root.OpenRead(testCase.path)
			assertUnsafePath(t, err, testCase.path)
		})
	}
}

// TestOpenReadRejectsMagicLink covers a /proc magic link target.
//
// Note on coverage honesty: this case is rejected by RESOLVE_NO_SYMLINKS
// before RESOLVE_NO_MAGICLINKS is consulted, because a magic link is reached
// through a symlink. Mutation testing confirmed that removing
// RESOLVE_NO_MAGICLINKS alone does not fail any test. The flag is retained as
// defense in depth for future accessors that might relax the symlink guard;
// it is not independently exercised here, and this comment exists so a later
// reader does not mistake it for proven coverage.
func TestOpenReadRejectsMagicLink(t *testing.T) {
	root, dir := newRoot(t)

	if err := os.Symlink("/proc/self/exe", filepath.Join(dir, "magic")); err != nil {
		t.Skipf("cannot create magic link: %v", err)
	}
	_, err := root.OpenRead("magic")
	assertUnsafePath(t, err, "magic")
}

// TestOpenReadRejectsOverlongPath proves the PathBytes bound is enforced.
func TestOpenReadRejectsOverlongPath(t *testing.T) {
	root, _ := newRoot(t)

	_, err := root.OpenRead(strings.Repeat("a", 4096))
	assertUnsafePath(t, err)
}

// TestOpenReadRejectsSymlinkReplacementRace is the decisive test: it swaps a
// real directory component for a symlink after the path is chosen. A lexical
// check would pass; only a kernel-enforced openat2 resolution rejects it.
func TestOpenReadRejectsSymlinkReplacementRace(t *testing.T) {
	root, dir := newRoot(t)

	outside := t.TempDir()
	mustWrite(t, filepath.Join(outside, "file.txt"), "secret\n")

	// The path validates against a real directory first.
	if _, err := root.OpenRead("nested/deep/file.txt"); err != nil {
		t.Fatalf("precondition open failed: %v", err)
	}

	// Now replace the "nested" component with a symlink escaping the root.
	if err := os.RemoveAll(filepath.Join(dir, "nested")); err != nil {
		t.Fatalf("remove nested: %v", err)
	}
	if err := os.Symlink(outside, filepath.Join(dir, "nested")); err != nil {
		t.Fatalf("symlink nested: %v", err)
	}

	_, err := root.OpenRead("nested/file.txt")
	assertUnsafePath(t, err, outside)
}

// TestOpenReadRejectsSymlinkResolvingInsideRoot is the case that actually pins
// RESOLVE_NO_SYMLINKS. An intermediate symlink whose target stays beneath the
// root is not caught by RESOLVE_BENEATH, and O_NOFOLLOW only guards the final
// component, so without the explicit no-symlink guard this open would succeed.
func TestOpenReadRejectsSymlinkResolvingInsideRoot(t *testing.T) {
	root, dir := newRoot(t)

	// "inner" points at a real directory inside the same root.
	if err := os.Symlink("nested", filepath.Join(dir, "inner")); err != nil {
		t.Fatalf("symlink inner: %v", err)
	}

	// Sanity: the target is genuinely reachable without the symlink.
	if _, err := root.OpenRead("nested/deep/file.txt"); err != nil {
		t.Fatalf("precondition failed: %v", err)
	}

	_, err := root.OpenRead("inner/deep/file.txt")
	assertUnsafePath(t, err, "inner/deep/file.txt")
}

// TestOpenDirRejectsSymlinkedDirectoryInsideRoot pins the same guard for the
// directory accessor.
func TestOpenDirRejectsSymlinkedDirectoryInsideRoot(t *testing.T) {
	root, dir := newRoot(t)

	if err := os.Symlink("nested", filepath.Join(dir, "inner")); err != nil {
		t.Fatalf("symlink inner: %v", err)
	}

	_, err := root.OpenDir("inner")
	assertUnsafePath(t, err, "inner")
}

// TestAtomicReplaceRejectsSymlinkedParentInsideRoot proves a symlinked parent
// directory cannot be used as a write path even when it stays beneath the root.
func TestAtomicReplaceRejectsSymlinkedParentInsideRoot(t *testing.T) {
	root, dir := newRoot(t)

	if err := os.Symlink("nested", filepath.Join(dir, "inner")); err != nil {
		t.Fatalf("symlink inner: %v", err)
	}

	err := root.AtomicReplace("inner/written.txt", strings.NewReader("x\n"), 0o644)
	assertUnsafePath(t, err, "inner/written.txt")
}

func TestOpenRootRejectsNonDirectory(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "file.txt")
	mustWrite(t, path, "x\n")

	_, err := OpenRoot(path)
	assertUnsafePath(t, err, path)
}

func TestOpenRootRejectsMissingDirectory(t *testing.T) {
	_, err := OpenRoot(filepath.Join(t.TempDir(), "absent"))
	assertUnsafePath(t, err)
}

func TestCloseIsIdempotentAndReleasesTheDescriptor(t *testing.T) {
	root, _ := newRoot(t)

	if err := root.Close(); err != nil {
		t.Fatalf("first Close: %v", err)
	}
	if err := root.Close(); err != nil {
		t.Errorf("second Close returned an error: %v", err)
	}
	if _, err := root.OpenRead("manifest.yml"); err == nil {
		t.Error("OpenRead succeeded after Close")
	}
}

func TestAtomicReplaceWritesNewFile(t *testing.T) {
	root, dir := newRoot(t)

	if err := root.AtomicReplace("out.txt", strings.NewReader("written\n"), 0o644); err != nil {
		t.Fatalf("AtomicReplace: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(dir, "out.txt"))
	if err != nil {
		t.Fatalf("read back: %v", err)
	}
	if string(data) != "written\n" {
		t.Errorf("contents = %q, want %q", data, "written\n")
	}

	info, err := os.Lstat(filepath.Join(dir, "out.txt"))
	if err != nil {
		t.Fatalf("lstat: %v", err)
	}
	if info.Mode().Perm() != 0o644 {
		t.Errorf("mode = %v, want 0644", info.Mode().Perm())
	}
}

func TestAtomicReplaceOverwritesExistingFile(t *testing.T) {
	root, dir := newRoot(t)

	if err := root.AtomicReplace("manifest.yml", strings.NewReader("version: 2\n"), 0o644); err != nil {
		t.Fatalf("AtomicReplace: %v", err)
	}
	data, err := os.ReadFile(filepath.Join(dir, "manifest.yml"))
	if err != nil {
		t.Fatalf("read back: %v", err)
	}
	if string(data) != "version: 2\n" {
		t.Errorf("contents = %q, want %q", data, "version: 2\n")
	}
}

// TestAtomicReplaceLeavesNoTemporaryFile proves the staging file is renamed or
// cleaned up rather than left behind.
func TestAtomicReplaceLeavesNoTemporaryFile(t *testing.T) {
	root, dir := newRoot(t)

	if err := root.AtomicReplace("out.txt", strings.NewReader("x\n"), 0o644); err != nil {
		t.Fatalf("AtomicReplace: %v", err)
	}

	entries, err := os.ReadDir(dir)
	if err != nil {
		t.Fatalf("read dir: %v", err)
	}
	for _, entry := range entries {
		name := entry.Name()
		if name != "manifest.yml" && name != "nested" && name != "out.txt" {
			t.Errorf("unexpected leftover entry %q", name)
		}
	}
}

// TestAtomicReplaceRejectsSymlinkDestination proves a pre-planted symlink at the
// destination cannot redirect a write outside the root.
func TestAtomicReplaceRejectsSymlinkDestination(t *testing.T) {
	root, dir := newRoot(t)

	outside := filepath.Join(t.TempDir(), "target.txt")
	mustWrite(t, outside, "original\n")
	if err := os.Symlink(outside, filepath.Join(dir, "link.txt")); err != nil {
		t.Fatalf("symlink: %v", err)
	}

	err := root.AtomicReplace("link.txt", strings.NewReader("hijacked\n"), 0o644)
	assertUnsafePath(t, err, outside)

	data, readErr := os.ReadFile(outside)
	if readErr != nil {
		t.Fatalf("read outside: %v", readErr)
	}
	if string(data) != "original\n" {
		t.Errorf("symlink target was modified: %q", data)
	}
}

func TestAtomicReplaceRejectsUnsafePaths(t *testing.T) {
	root, _ := newRoot(t)

	for _, path := range []string{"", "/etc/passwd", "../outside.txt", "absent/file.txt"} {
		t.Run(path, func(t *testing.T) {
			err := root.AtomicReplace(path, strings.NewReader("x\n"), 0o644)
			assertUnsafePath(t, err, path)
		})
	}
}

func TestAtomicReplaceRejectsNilReader(t *testing.T) {
	root, _ := newRoot(t)

	if err := root.AtomicReplace("out.txt", nil, 0o644); err == nil {
		t.Error("expected a failure for a nil source reader")
	}
}

func TestAtomicReplaceCopiesLargeContent(t *testing.T) {
	root, dir := newRoot(t)

	payload := bytes.Repeat([]byte("z"), 1<<20)
	if err := root.AtomicReplace("big.bin", bytes.NewReader(payload), 0o644); err != nil {
		t.Fatalf("AtomicReplace: %v", err)
	}
	data, err := os.ReadFile(filepath.Join(dir, "big.bin"))
	if err != nil {
		t.Fatalf("read back: %v", err)
	}
	if !bytes.Equal(data, payload) {
		t.Error("large content round trip mismatch")
	}
}

// TestRootSatisfiesManifestReader is the integration seam Task 2 orchestration
// already depends on; it must hold without an adapter.
func TestRootSatisfiesManifestReader(t *testing.T) {
	var _ manifest.Reader = (*Root)(nil)

	root, dir := newRoot(t)
	mustWrite(t, filepath.Join(dir, "demo.yml"), validManifest)
	if err := os.MkdirAll(filepath.Join(dir, ".github", "demos", "fixtures"), 0o755); err != nil {
		t.Fatalf("create fixtures: %v", err)
	}
	mustWrite(t, filepath.Join(dir, ".github", "demos", "readme.tape"), "Type \"ll\"\nEnter\n")
	if err := os.MkdirAll(filepath.Join(dir, "docs"), 0o755); err != nil {
		t.Fatalf("create docs: %v", err)
	}
	mustWrite(t, filepath.Join(dir, "docs", "README.md"), "# Demo\n")

	if _, err := manifest.Load(root, "demo.yml"); err != nil {
		t.Fatalf("manifest.Load through repopath.Root failed: %v", err)
	}
}

const validManifest = `version: 1
scenario: .github/demos/readme.tape
fixtures: .github/demos/fixtures
outputs:
  gif: docs/assets/readme-demo.gif
  png: docs/assets/readme-demo.png
readme:
  path: docs/README.md
  alt: Short description of the behavior shown in the terminal demo.
`
