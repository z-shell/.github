# 8. Branching Model

- **Status:** PROPOSED
- **Date:** 2026-05-29
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

The org's repositories do not share a single branching model, and the
inconsistency is real, not cosmetic:

- Some repos run a `next` → `main` integration flow (`src`, `wiki`, `zi`,
  `zsh-lint`, `zsh-eza`).
- Others are trunk-based on `main` only (`zd`, packaged `zsh`,
  `z-a-meta-plugins`, `zsh-fancy-completions`, `zunit`, `.github`).

The meta-workspace catalog (`workspace/repos.yml`) had drifted from this reality
and had to be reconciled by inspecting live remotes. The root cause is that no
decision says *which class of repo uses a `next` branch and which does not*, so
each repo's model is discovered empirically rather than governed. `zsh-lint`
recently gained a `next` branch during its Go reboot, which re-surfaced the
ambiguity.

`decisions/0007-release-publication-flow.md` already defines four repository
classes by delivery model. Branching should be derived from those classes rather
than decided per repo, so the catalog stops drifting at the source.

## Decision

Branch model follows the ADR-0007 repository class.

1. **Continuously deployed artifacts** (`wiki`, `src`, `zd` images) — use a
   `next` → `main` integration branch. `next` is the default development branch;
   merging to `main` is the deploy/publication boundary. Branch names:
   `feature-<id>`, `bug-<id>`, `hotfix-<id>`; hotfixes branch from `main`, all
   other work from `next`.
2. **Versioned tools and packages** (`zunit`, `zsh-lint`, packaged `zsh`) — `main`
   is continuously validated development output; publication is a `vX.Y.Z` tag
   (per ADR-0007). A `next` branch is **optional**: adopt it only when the repo's
   change volume justifies an integration buffer (as `zsh-lint` did for its Go
   reboot). Trunk-on-`main` is the default for low-volume tools.
3. **Git-consumed source** (`zi`, most plugins/annexes) — `next` → `main` where an
   integration branch adds value (`zi`, `zsh-eza`); trunk-on-`main` is acceptable
   for small, low-churn plugins (`z-a-meta-plugins`, `zsh-fancy-completions`).
   `main` is always the consumable ref.
4. **Meta/infrastructure** (`.github`) — trunk-based on `main`. No `next` branch.

`workspace/repos.yml` records each repo's actual branch model and notes when a
repo is trunk-only. Whenever a repo adds or removes a `next` branch, the catalog
entry is updated in the same change.

## Consequences

- `workspace/repos.yml` has an authoritative rule to validate against, instead of
  drifting from empirical discovery.
- New repos inherit a branch model from their ADR-0007 class at creation time.
- The default-branch and branch-naming guidance in the workspace `CLAUDE.md`
  ("default development branch `next`") is understood as the *integration-flow*
  default, not a universal rule — trunk-only repos are explicitly sanctioned by
  this ADR for classes 2–4 where noted.
- Promotion from `next` to `main` is a publication boundary only for class 1
  (deploy) repos; for other classes the merge validates but does not mint a
  release (consistent with ADR-0007).

## Alternatives considered

- **One model for all repos (`next` → `main` everywhere).** Rejected: forces an
  integration branch onto single-maintainer, low-churn plugins where it only adds
  ceremony, and onto `.github` where there is nothing to integrate.
- **Trunk-only everywhere.** Rejected: the continuously deployed repos benefit
  from a staging branch before a change goes live, and `zi`'s scale warrants an
  integration buffer.
- **Leave it per-repo and informal.** Rejected: that is the status quo that let
  the catalog drift and required a manual remote audit to repair.

## References

- `decisions/0007-release-publication-flow.md` — repository classes this builds on.
- `workspace/repos.yml` (meta-workspace) — per-repo branch model catalog.
- `decisions/0003-conventional-commits.md` — commit/branch naming conventions.
