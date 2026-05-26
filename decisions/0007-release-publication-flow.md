# 7. Release and Publication Flow

- **Status:** ACCEPTED
- **Date:** 2026-05-26
- **Deciders:** ss-o, Claude Code
- **Supersedes:** None
- **Superseded by:** None

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

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd` images): validate on
   the development branch; deploy via the repo's existing delivery model. No
   tag-driven changelog/release automation unless a separate packaged artifact
   appears.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, packaged `zsh`):
   `main` is continuously validated development output; **annotated semantic
   tags `vX.Y.Z` are the publication boundary**. User-facing releases are minted
   only from those tags.
3. **Git-consumed source** (`zi`, most plugins/annexes): Conventional Commits for
   clean history; CI is validation-only; **no release automation** unless the
   repo later gains a separate packaged artifact.
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
- **`zsh-lint`** — a Zsh plugin consumed from source, with **no build artifact**.
  Its release is a tagged GitHub release with generated notes only (no upload).
  (`zsh-lint#21`.)
- **packaged `zsh`** — deferred: confirm what it publishes (npm package vs.
  metadata) before wiring a release, since the artifact determines the steps.
  (`zsh#8`.)
- **`zi`** — class 3, git-consumed; **no release automation added**. Its
  `next → main → tag` boundary (`zi#346`) is governed by this policy but no
  workflow or code change is made to `zi` under this ADR.

## Consequences

- `runbooks/release.md` is updated to reference this accepted ADR rather than a
  pending one.
- `zsh-lint` gains a notes-only tag-driven `release.yml`.
- `release-please` is not adopted org-wide; it remains available to revisit per
  repo if a maintainer wants automated changelog/version PRs.
- Class-3 repos (incl. `zi`) keep validation-only CI; tagging there is a manual,
  policy-governed act, not automation.

## Alternatives considered

- **`release-please` as the org standard.** Rejected for now: heavier machinery
  (bot-maintained release PRs, version-bump commits) than the tag boundary
  requires, and `runbooks/release.md` lists it only as a *pilot candidate*, not a
  decision. Can be piloted per repo later without contradicting this ADR.
- **One release model for all repos.** Rejected: continuously-deployed and
  git-consumed repos do not benefit from tag-driven release artifacts.
- **Defer the ADR, keep guidance informal.** Rejected: the runbook explicitly
  waited on this decision; leaving it open invites drift.

## References

- `runbooks/release.md` — repo-class release coordination guidance.
- `z-shell/zunit` `.github/workflows/release.yml` — reference tag-driven flow.
- `decisions/0003-conventional-commits.md` — history format this builds on.
- Tracker: `zsh-lint#21`, `zsh#8`, `zi#346`.
