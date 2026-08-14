# 9. Testing and CI Strategy

- **Status:** ACCEPTED
- **Date:** 2026-07-25
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

CI exists across the org's repos but its scope is decided per repo and per
workflow rather than from a shared policy. The result is uneven: some repos run
`zsh -n` syntax checks plus `zcompile`, others add ZUnit suites, `zsh-lint` has
Go tests, and the container repo builds a multi-arch matrix. There is no written
statement of _what level of testing each repository class owes_, which makes it
hard to know whether a repo is under- or over-tested, and what a reviewer should
require before merge.

ADR-0007 classified repositories by delivery model and ADR-0008 establishes a
branch model informed by those classes. This ADR similarly establishes a
target CI scope by class, accepted with owned rollout gaps: it does not claim
that every listed control is already live or configured as a required check.

## Decision

Required CI scope follows the ADR-0007 repository class. Every class shares a
common target baseline; higher-risk classes add to it. Live rollout gaps and
the dated evidence behind them are tracked in issue #454 rather than copied
into this ADR as a transient workflow inventory.

### Baseline (all repos)

Every item below is target policy — the baseline every repository is expected
to meet, not an assertion that each control is already live everywhere. Live
rollout status per repository is tracked in issue #454, not restated here.

- Workflows comply with the org workflow conventions (SHA-pinned actions,
  least-privilege `permissions:`, `concurrency:`, no-emoji `name:` per ADR-0005,
  kebab-case filenames), defined in
  `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
  and `decisions/0005-workflow-naming-conventions.md`; `AGENTS.md` only
  summarizes them.
- Zsh sources pass `zsh -n` (syntax) and `zcompile` (compile) checks.
- Dependency-update and vulnerability-remediation ownership follows accepted
  ADR-0012. ADR-0012 does **not** establish organization-wide secret-scanning
  coverage; that requires separately configured and verified controls.
- Conventional Commits (ADR-0003), PR-title validation, and the
  disallowed-trailer rule are enforced in CI. None of these is a live org-wide
  gate today: a sweep of the default branches of all 86 active, non-fork,
  non-archived repositories found no workflow that runs the
  `DISALLOWED_TRAILER_PATTERN` check or validates commit messages. Non-default
  branches were not swept. The only implementation is a `commit-lint` workflow
  on the `next` branch of `z-shell/zi`, which has never reached a default
  branch.

### By class

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd`) — the build succeeds
   on the development branch before deploy. The target checks cover the wiki's
   lint and production build, `zd`'s Docker build matrix, and `src`'s
   installer/loader validation, plus CodeQL where a supported language is
   present.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, `zpmod`, packaged
   `zsh`) — a full functional suite is **required** before a release tag is cut,
   defined per tool: `zunit`'s release workflow must run its own native suite on
   the exact tag commit before publication, since prior branch checks alone do
   not prove the released commit; packaged `zsh`'s gate is metadata/manifest
   validation plus a clean disposable install and a startup/version smoke test,
   all on the exact tag commit, since metadata-only validation alone is not a
   functional suite; `zsh-lint`'s gate is `go test` on the exact tag commit;
   `zpmod`'s full functional suite likewise runs on the exact tag commit before
   publication. Compiled tools additionally run an appropriate SAST control,
   such as CodeQL or `gosec`; a release artifact is part of the security surface
   governed by `decisions/0010-security-incident-response.md`.
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

Under the target policy, each repository marks its class-appropriate checks as
required for merge to its publication branch (`main`, or `next` → `main` per
ADR-0008). Validation-only repositories require the baseline; class-2
repositories additionally require the functional suite. Required checks,
development-branch validation, SAST coverage, and the release-suite gate are
each verified repository by repository through owning issues; the presence of
a workflow file is not by itself treated as proof that a check is required or
that a ruleset enforces it.

## Consequences

- A reviewer can determine the target CI bar from the repository's class
  instead of inferring policy from each workflow.
- New repositories have an explicit target CI scope for their class.
- "Validation-only for git-consumed repositories" becomes an explicit rule,
  discouraging release machinery in class-3 repositories (consistent with
  ADR-0007).
- The testing instruction file (`.github/instructions/testing.instructions.md`)
  currently reads as present-tense enforcement (for example, it states
  Conventional Commits and the disallowed-trailer check "are enforced"). That
  is target-state language, not evidence of current conformance, and the file
  should be reconciled to say so. It is not changed by this decision.

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
- `decisions/0012-hybrid-dependency-management.md` — dependency-update and
  vulnerability-remediation ownership.
- `decisions/0010-security-incident-response.md` — SAST/release security surface.
- `z-shell/zd` `.github/workflows/test-native.yml` — reusable ZUnit workflow.
- [Issue #454](https://github.com/z-shell/.github/issues/454) — dated rollout-gap
  evidence and maintainer decision record.
- [`z-shell/zpmod#70`](https://github.com/z-shell/zpmod/issues/70) — owning
  remediation issue for the class-2 functional-suite gate.
