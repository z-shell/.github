// Package repopath opens untrusted repository paths inside a containment
// boundary.
//
// Every open of a caller-supplied relative path is resolved by the kernel
// through openat2 with RESOLVE_BENEATH, RESOLVE_NO_SYMLINKS, and
// RESOLVE_NO_MAGICLINKS, plus O_NOFOLLOW on the final component. This package
// deliberately never resolves a path with filepath.EvalSymlinks followed by an
// ordinary open: that pattern is racy, because a component can be replaced
// between the check and the open.
//
// Lexical validation here is a fast, sanitized rejection for obviously unsafe
// input. It is never the security boundary; the kernel is.
package repopath

import (
	"errors"
	"strings"

	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/failure"
	"github.com/z-shell/.github/tools/readme-terminal-demo/internal/limits"
)

// unsafePath builds the single sanitized failure this package returns. The
// field names a bounded category only; it never carries the offending path,
// which may contain untrusted repository text.
func unsafePath(category string, err error) error {
	return failure.E(failure.UnsafePath, failure.StageSource, category, failure.RuleSourceMutated, err)
}

// validateRelative rejects input that cannot be a safe repository-relative
// path. Passing this check does not authorize an open on its own.
func validateRelative(rel string) error {
	bounds := limits.V1()

	if rel == "" {
		return unsafePath("path", errors.New("path is required"))
	}
	if len(rel) > bounds.PathBytes {
		return unsafePath("path", errors.New("path exceeds its byte bound"))
	}
	if strings.ContainsRune(rel, 0) {
		return unsafePath("path", errors.New("path contains a NUL byte"))
	}
	if strings.HasPrefix(rel, "/") {
		return unsafePath("path", errors.New("path must be repository-relative"))
	}
	if strings.Contains(rel, `\`) {
		return unsafePath("path", errors.New("path contains a backslash"))
	}

	for _, segment := range strings.Split(rel, "/") {
		switch segment {
		case "":
			return unsafePath("path", errors.New("path contains an empty component"))
		case ".", "..":
			return unsafePath("path", errors.New("path contains a relative component"))
		}
	}
	return nil
}
