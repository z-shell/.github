# 7. Release and Publication Flow

- **Status:** ACCEPTED
- **Date:** 2026-05-26
- **Deciders:** ss-o
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

Zi may automate release preparation and publication under this contract:

- a successful promotion to `main` may compute the next semantic version and
  draft release notes, but preparation never creates or pushes a tag;
- a maintainer authorizes publication by pushing an annotated, signed
  `vX.Y.Z` tag to the exact verified `main` commit;
- the tag-triggered workflow verifies the signature, exact target, and
  successful required workflows on that commit before publishing the GitHub
  release; and
- Zi does not adopt `release-please` or a stored version file. Runtime version
  reporting continues to derive from Git metadata.

The signed tag is the human approval boundary. Automation after that boundary
may be idempotent, but it must fail closed when the tag or validation evidence
does not match the contract.

## Consequences

- `runbooks/release.md` is updated to reference this accepted ADR rather than a
  pending one.
- `zsh-lint` gains a notes-only tag-driven `release.yml`.
- `release-please` is not adopted org-wide; it remains available to revisit per
  repo if a maintainer wants automated changelog/version PRs.
- Class-3 repositories remain validation-only by default. Zi is the named
  exception: release preparation and publication may be automated, while tag
  creation remains a manual, policy-governed act.

## Alternatives considered

- **`release-please` as the org standard.** Rejected for now: heavier machinery
  (bot-maintained release PRs, version-bump commits) than the tag boundary
  requires, and `runbooks/release.md` lists it only as a _pilot candidate_, not a
  decision. Can be piloted per repo later without contradicting this ADR.
- **One release model for all repos.** Rejected: continuously-deployed and
  git-consumed repos do not benefit from tag-driven release artifacts.
- **Create a Zi tag on every promotion.** Rejected: not every promotion needs a
  milestone release, and an automatically created tag would remove the exact
  human publication approval boundary.
- **Defer the ADR, keep guidance informal.** Rejected: the runbook explicitly
  waited on this decision; leaving it open invites drift.

## References

- `runbooks/release.md` — repo-class release coordination guidance.
- `z-shell/zunit` `.github/workflows/release.yml` — reference tag-driven flow.
- `decisions/0003-conventional-commits.md` — history format this builds on.
- Tracker: `zsh-lint#21`, `zsh#8`, `zi#346`.
- [Issue #583](https://github.com/z-shell/.github/issues/583) and
  [zi#468](https://github.com/z-shell/zi/issues/468): approved Zi
  milestone-release automation.
- [Issue #497](https://github.com/z-shell/.github/issues/497) and
  [z-shell/zpmod#70](https://github.com/z-shell/zpmod/issues/70): accepted
  `zpmod` classification and owning repository remediation.
