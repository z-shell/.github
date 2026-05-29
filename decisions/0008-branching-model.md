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

Branch model follows the ADR-0007 repository class, and the **canonical
per-repo table below is the authoritative source** that `workspace/repos.yml`
derives from. There is no per-repo discretion: a repo's branch model is whatever
this table says, and changing it requires editing this ADR (a superseding
decision), not an ad-hoc branch creation.

### Canonical branch model

| Repo                   | Class | Branch model     | Development branch | Publication boundary        |
| ---------------------- | ----- | ---------------- | ------------------ | --------------------------- |
| `wiki`                 | 1     | `next` → `main`  | `next`             | merge to `main` (deploy)    |
| `src`                  | 1     | `next` → `main`  | `next`             | merge to `main` (deploy)    |
| `zd`                   | 1     | `next` → `main`  | `next`             | merge to `main` (image)     |
| `zunit`                | 2     | trunk on `main`  | `main`             | `vX.Y.Z` tag                |
| `zsh-lint`             | 2     | `next` → `main`  | `next`             | `vX.Y.Z` tag                |
| packaged `zsh`         | 2     | trunk on `main`  | `main`             | `vX.Y.Z` tag (deferred)     |
| `zi`                   | 3     | `next` → `main`  | `next`             | `main` is consumable ref    |
| `zsh-eza`              | 3     | `next` → `main`  | `next`             | `main` is consumable ref    |
| `z-a-meta-plugins`     | 3     | trunk on `main`  | `main`             | `main` is consumable ref    |
| `zsh-fancy-completions`| 3     | trunk on `main`  | `main`             | `main` is consumable ref    |
| `.github`              | 4     | trunk on `main`  | `main`             | n/a                         |

### Rules

- **Class 1 (deploy):** `next` → `main`; merging to `main` is the deploy boundary.
- **Class 2 (versioned tools):** `main` is continuously validated; publication is a
  `vX.Y.Z` tag (ADR-0007). A `next` branch is used only where the table assigns it
  (`zsh-lint`, for its Go reboot); the default is trunk-on-`main`.
- **Class 3 (git-consumed):** `main` is always the consumable ref. High-churn repos
  use `next` → `main` (`zi`, `zsh-eza`); low-churn plugins are trunk-on-`main`.
- **Class 4 (meta):** trunk on `main`; no `next`.
- **Branch naming (all classes):** `feature-<id>`, `bug-<id>`, `hotfix-<id>`.
  Hotfixes branch from `main`; other work branches from the repo's development
  branch (the "Development branch" column). For trunk repos, feature branches
  also start from `main`.

`workspace/repos.yml` mirrors this table and must match it. A repo's branch model
is not changed by creating a branch — it is changed by amending this ADR (or a
superseding ADR) and updating the catalog in the same change.

## Consequences

- `workspace/repos.yml` derives from the canonical table above, so drift is
  structurally prevented: the catalog is validated against an explicit table, not
  "use judgment."
- New repos are added to the table (with their ADR-0007 class) as part of repo
  creation, before the first branch is cut.
- **Action on acceptance:** the workspace `CLAUDE.md` currently states "default
  development branch: `next` … all other work branches from `next`" as a universal
  rule. On acceptance, update that section to reference this ADR's per-repo table
  so agents do not get conflicting guidance for trunk-only repos. (Not done while
  this ADR is PROPOSED — `CLAUDE.md` should not cite an unaccepted decision.)
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
