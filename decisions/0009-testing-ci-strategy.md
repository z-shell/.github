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

- All workflows comply with the org workflow conventions: SHA-pinned actions,
  top-level least-privilege `permissions:`, `concurrency:` for push/PR triggers,
  no-emoji workflow/job `name:` (ADR-0005), kebab-case filenames.
- Zsh sources pass `zsh -n` (syntax) and `zcompile` (compile) checks.
- Commit/PR-title lint enforces Conventional Commits (ADR-0003) and rejects the
  disallowed-trailer pattern.

### By class

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd`) — build must succeed
   on the development branch before deploy. Wiki runs lint (ESLint/Stylelint) and
   a production build; `zd` runs the Docker build matrix; `src` validates the
   installer/loader. CodeQL where a supported language is present.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, packaged `zsh`) — full
   functional test suite is **required** and gates release tags. ZUnit for Zsh
   tools; `go test` for the `zsh-lint` Go CLI. A release tag must not be cut from
   a commit whose suite is red.
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
- `z-shell/zd` `.github/workflows/test-native.yml` — reusable ZUnit workflow.
