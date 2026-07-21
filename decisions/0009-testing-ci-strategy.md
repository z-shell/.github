# 9. Testing and CI Strategy

- **Status:** PROPOSED
- **Date:** 2026-05-29
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

CI exists across the org's repos but its scope is decided per repo and per
workflow rather than from a shared policy. The result is uneven: some repos run
`zsh -n` syntax checks plus `zcompile`, others add ZUnit suites, `zsh-lint` has
Go tests, and the container repo builds a multi-arch matrix. There is no written
statement of *what level of testing each repository class owes*, which makes it
hard to know whether a repo is under- or over-tested, and what a reviewer should
require before merge.

ADR-0007 classified repos by delivery model and ADR-0008 derived branching from
those classes. Testing depth should be derived the same way, so CI scope is a
property of the repo class rather than an accident of history.

## Decision

Required CI scope follows the ADR-0007 repository class. Every class shares a
common baseline; higher-risk classes add to it.

### Baseline (all repos)

- All workflows comply with the org workflow conventions (SHA-pinned actions,
  least-privilege `permissions:`, `concurrency:`, no-emoji `name:` per ADR-0005,
  kebab-case filenames). These conventions are defined in the workspace `CLAUDE.md`
  and the CI instructions — this ADR references them rather than restating, so
  there is a single source of truth.
- Zsh sources pass `zsh -n` (syntax) and `zcompile` (compile) checks.
- Dependency and secret scanning per `decisions/0004-dependabot-unification.md`.
- **Target state (not yet a live org-wide control):** Conventional Commits
  (ADR-0003) and the disallowed-trailer rule enforced in CI. Neither is a live
  org-wide gate today: a sweep of every repository's default branch found no
  workflow that runs the `DISALLOWED_TRAILER_PATTERN` check or validates commit
  messages. The only implementation is a `commit-lint` workflow on the `next`
  branch of `z-shell/zi`, which has never reached a default branch. Both the
  trailer ban and Conventional Commits are convention-and-review until a shared
  commit/PR-title-lint check is promoted into a reusable workflow here and rolled
  out; that work is tracked separately.

### By class

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd`) — build must succeed
   on the development branch before deploy. Wiki runs lint (ESLint/Stylelint) and
   a production build; `zd` runs the Docker build matrix; `src` validates the
   installer/loader. CodeQL where a supported language is present.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, packaged `zsh`) — full
   functional test suite is **required** and gates release tags. ZUnit for Zsh
   tools; `go test` for the `zsh-lint` Go CLI. A release tag must not be cut from
   a commit whose suite is red. Compiled tools additionally run SAST (CodeQL
   and/or `gosec` for the `zsh-lint` Go CLI); a release artifact is part of the
   security surface governed by `decisions/0010-security-incident-response.md`.
3. **Git-consumed source** (`zi`, most plugins/annexes) — **validation-only**: the
   baseline checks above, plus ZUnit where the plugin ships tests. No release
   automation and no coverage gate; these repos are consumed from source and the
   bar is "does not break on load."
4. **Meta/infrastructure** (`.github`) — baseline plus workflow/markdown linting.

### Coverage

Coverage is **observed, not gated**, except where a class-2 tool chooses to set a
threshold for its own suite. The org does not impose a uniform coverage number;
ratcheting is a per-repo maintainer decision.

### Required checks

Each repo marks its class-appropriate checks as required for merge to its
publication branch (`main`, or `next`→`main` per ADR-0008). Validation-only repos
require the baseline; class-2 repos additionally require the functional suite.

## Consequences

- A reviewer can determine the expected CI bar from the repo's class instead of
  reading each workflow.
- New repos start with the correct CI scope for their class.
- "Validation-only for git-consumed repos" is now an explicit rule, preventing
  release machinery from creeping into class-3 repos (consistent with ADR-0007).
- The testing instruction file (`.github/instructions/testing.instructions.md`)
  operationalizes this ADR for day-to-day authoring.

## Alternatives considered

- **Uniform full test suite + coverage gate everywhere.** Rejected: imposes
  functional-suite and coverage overhead on git-consumed plugins where a load/
  syntax check is the meaningful bar, and slows low-churn repos for no benefit.
- **Leave CI scope per repo (status quo).** Rejected: produces uneven, undocumented
  expectations and no shared definition of "tested enough to merge/release."
- **Centralize all CI into reusable workflows only.** Deferred: reusable workflows
  (e.g. `zd`'s `test-native.yml`) are encouraged but mandating a single shared
  pipeline is heavier than the class-based baseline this ADR sets.

## References

- `decisions/0007-release-publication-flow.md` — repository classes.
- `decisions/0008-branching-model.md` — branch model per class.
- `decisions/0005-workflow-naming-conventions.md` — workflow naming baseline.
- `decisions/0004-dependabot-unification.md` — dependency scanning baseline.
- `decisions/0010-security-incident-response.md` — SAST/release security surface.
- `z-shell/zd` `.github/workflows/test-native.yml` — reusable ZUnit workflow.
