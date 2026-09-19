# 7. Release and Publication Flow

- **Status:** ACCEPTED
- **Date:** 2026-05-26
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** `decisions/0028-zi-promotion-is-release-authorization.md` (Zi milestone exception only)

## Context

The org maintains repositories with different delivery models — a continuously
deployed wiki and installer, container images, versioned CLI tools, and
git-consumed plugins/annexes. `runbooks/release.md` already describes a
repo-type-aware policy, but it explicitly stood "until the corresponding ADR is
accepted." Without an accepted decision, release behavior risked drifting
(e.g. forcing `release-please` onto repos that do not need it, or tagging repos
that are consumed directly from Git).

`zunit` already ships a working tag-driven release (`.github/workflows/release.yml`:
push a `vX.Y.Z` tag → verify the tag matches the built binary → `gh release
create --generate-notes`). That establishes the concrete pattern this ADR
formalizes.

## Decision

### Repository classes and release policy

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd` images): validate
   pull requests into `main` and the merged `main` commit; deploy via the
   repository's existing delivery controls. No
   tag-driven changelog/release automation unless a separate packaged artifact
   appears.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, `zpmod`, packaged
   `zsh`):
   `main` is continuously validated development output; **annotated semantic
   tags `vX.Y.Z` are the publication boundary**. User-facing releases are minted
   only from those tags.
3. **Git-consumed source** (`zi`, most plugins/annexes): Conventional Commits for
   clean history; CI is validation-only; **no release automation** unless the
   repo later gains a separate packaged artifact or this ADR names an explicit
   milestone-release exception.
4. **Meta/infrastructure** (`.github`): Conventional Commits; no release
   automation.

### Release mechanism for class 2 — simple tag-driven

The standard is the **`zunit` pattern**, not `release-please`:

- Trigger: `on: push: tags: ["v*.*.*"]`.
- `permissions: contents: write`; `concurrency` with `cancel-in-progress: false`
  (never cancel an in-flight release).
- Steps: checkout (SHA-pinned) → verify the tag is `vX.Y.Z` (and matches the
  built artifact's version where one exists) → build the artifact if any →
  `gh release create "$tag" --generate-notes` (idempotent: upload/`--clobber`
  if the release already exists).
- Reference untrusted tag input via `GITHUB_REF_NAME` env, never inline
  `${{ }}` interpolation in `run:`.

Per-repo application:

- **`zunit`** — reference implementation (builds the `zunit` binary, verifies
  the tag against `--version`). Already in place.
- **`zsh-lint`**: a standalone Go semantic-analyzer CLI. Its exact tag commit
  must pass the repository-owned Go tests and build verification before any
  release is published. Artifact packaging remains owned by that repository.
- **`zpmod`**: class 2, with annotated `vX.Y.Z` tags created only from reviewed,
  green `main` commits. Pages and documentation publish only from reviewed
  `main` commits; that continuous documentation surface does not replace the
  annotated tag as the versioned release boundary. (`z-shell/.github#497`,
  `z-shell/zpmod#70`.)
- **packaged `zsh`** — deferred: confirm what it publishes (npm package vs.
  metadata) before wiring a release, since the artifact determines the steps.
  (`zsh#8`.)
- **`zi`**: class 3, git-consumed, with approval-gated milestone automation. Its
  `next` to stable `main` promotion is governed by ADR-0019. The named
  milestone-release exception below applies without changing `main` as the
  stable Git-consumption boundary.

### Zi milestone-release exception

ADR-0028 supersedes this exception. A reviewed `next` to `main` promotion is now Zi's human publication boundary when the promoted range contains releasable commits. Zi displays the version and release-note plan before merge, then creates the annotated tag and GitHub release only after every required workflow succeeds on the exact merge SHA. The maintainer-signed tag path remains available for recovery.

## Consequences

- `runbooks/release.md` is updated to reference this accepted ADR rather than a
  pending one.
- `zsh-lint` gains a notes-only tag-driven `release.yml`.
- `release-please` is not adopted org-wide; it remains available to revisit per
  repo if a maintainer wants automated changelog/version PRs.
- Class-3 repositories remain validation-only by default. Zi is the named
  exception governed by ADR-0028.

## Alternatives considered

- **`release-please` as the org standard.** Rejected for now: heavier machinery
  (bot-maintained release PRs, version-bump commits) than the tag boundary
  requires, and `runbooks/release.md` lists it only as a _pilot candidate_, not a
  decision. Can be piloted per repo later without contradicting this ADR.
- **One release model for all repos.** Rejected: continuously-deployed and
  git-consumed repos do not benefit from tag-driven release artifacts.
- **Create a Zi tag without a pre-merge plan or exact-SHA validation.** Rejected:
  automation must identify releasable commits before merge and must fail closed
  until every required workflow succeeds on the exact promotion merge SHA.
- **Defer the ADR, keep guidance informal.** Rejected: the runbook explicitly
  waited on this decision; leaving it open invites drift.

## References

- `runbooks/release.md` — repo-class release coordination guidance.
- `z-shell/zunit` `.github/workflows/release.yml` — reference tag-driven flow.
- `decisions/0003-conventional-commits.md` — history format this builds on.
- Tracker: `zsh-lint#21`, `zsh#8`, `zi#346`.
- [Issue #583](https://github.com/z-shell/.github/issues/583) and
  [zi#468](https://github.com/z-shell/zi/issues/468): approved Zi
  milestone-release automation, superseded for the normal path by ADR-0028.
- [ADR-0028](0028-zi-promotion-is-release-authorization.md): Zi promotion as
  release authorization.
- [Issue #497](https://github.com/z-shell/.github/issues/497) and
  [z-shell/zpmod#70](https://github.com/z-shell/zpmod/issues/70): accepted
  `zpmod` classification and owning repository remediation.
