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

An audit on 2026-07-18 found that all listed repositories use `main` as their
GitHub default branch. Only `src`, `wiki`, `zi`, `zsh-lint`, and `zsh-eza` have
a live `next` branch for development or integration. In this ADR, **GitHub
default branch** and **development branch** are therefore separate concepts.

The private meta-workspace catalog (`workspace/repos.yml`) is still drifted. Its
`default_branch` field conflates those concepts, and some entries name `next`
for repositories that do not have that branch. The catalog has not yet been
reconciled; that is a separate meta-workspace change after a maintainer decides
whether to accept this proposal.

`decisions/0007-release-publication-flow.md` already defines four repository
classes by delivery model. Those classes constrain publication behavior, but
the live branch inventory shows that class alone does not select a repository's
development branch.

## Decision

If accepted, the **canonical per-repo table below becomes the authoritative
source** for the development branch and branch model. The ADR-0007 repository
class is an _input_ to the choice because it sets the publication boundary and
a default, but it does **not** by itself determine the branch model — repo
churn/scale does. Within class 1, `wiki`/`src` use `next` → `main` while `zd` is
trunk-only; within class 2, `zsh-lint` uses `next` while `zunit` is trunk. Under
this proposal, changing a repository's assigned model requires amending this
ADR (or a superseding one), not merely creating or deleting a branch.

### Canonical branch model

| Repo                    | Class | Branch model    | Development branch | Publication boundary     |
| ----------------------- | ----- | --------------- | ------------------ | ------------------------ |
| `wiki`                  | 1     | `next` → `main` | `next`             | merge to `main` (deploy) |
| `src`                   | 1     | `next` → `main` | `next`             | merge to `main` (deploy) |
| `zd`                    | 1     | trunk on `main` | `main`             | push to `main` (image)   |
| `zunit`                 | 2     | trunk on `main` | `main`             | `vX.Y.Z` tag             |
| `zsh-lint`              | 2     | `next` → `main` | `next`             | `vX.Y.Z` tag             |
| packaged `zsh`          | 2     | trunk on `main` | `main`             | `vX.Y.Z` tag (deferred)  |
| `zi`                    | 3     | `next` → `main` | `next`             | `main` is consumable ref |
| `zsh-eza`               | 3     | `next` → `main` | `next`             | `main` is consumable ref |
| `z-a-meta-plugins`      | 3     | trunk on `main` | `main`             | `main` is consumable ref |
| `zsh-fancy-completions` | 3     | trunk on `main` | `main`             | `main` is consumable ref |
| `.github`               | 4     | trunk on `main` | `main`             | n/a                      |

The publication-boundary column states the proposed policy, not a complete
inventory of live workflow triggers. At the 2026-07-18 audit, `src` and `zd`
also had semantic-tag publication triggers that the table does not capture.
Whether those triggers remain accepted class-1 exceptions is a maintainer
decision.

### How the class informs the default

- **Class 1 (deploy):** `main` is the deploy ref. A `next` → `main` staging buffer
  is used where deploy traffic justifies it (`wiki`, `src`); `zd` deploys directly
  from `main`.
- **Class 2 (versioned tools):** `main` is continuously validated; publication is a
  `vX.Y.Z` tag (ADR-0007). Default is trunk-on-`main`; `next` is used only where the
  table assigns it (`zsh-lint`, for its Go reboot).
- **Class 3 (git-consumed):** `main` is always the consumable ref. High-churn repos
  use `next` → `main` (`zi`, `zsh-eza`); low-churn plugins are trunk-on-`main`.
- **Class 4 (meta):** trunk on `main`; no `next`.
- **Branch naming (all classes):** `feature-<id>`, `bug-<id>`, `hotfix-<id>`.
  Hotfixes branch from `main`; other work branches from the repo's development
  branch (the "Development branch" column). For trunk repos, feature branches also
  start from `main`.

If this ADR is accepted, the private catalog/schema and root agent guidance need
a separate meta-workspace reconciliation. They are deliberately not changed by
this public factual-reconciliation draft.

## Decision review required

Before acceptance, a maintainer must:

1. Confirm that GitHub defaults remain `main` while the table's development
   branch identifies the normal integration base.
2. Decide whether the live `src` and `zd` semantic-tag publication triggers are
   accepted exceptions or whether the proposed publication wording must change.
3. Accept, amend, supersede, or reject this proposal and record the decider and
   decision date.

## Consequences

- If accepted, the table gives branch-policy audits an explicit public
  comparison point; the ADR alone does not prevent catalog or repository drift.
- New repositories would be added to the table (with their ADR-0007 class) as
  part of repository creation, before the first branch is cut.
- **Action on acceptance:** the private meta-workspace root guidance currently
  states "default development branch: `next` … all other work branches from
  `next`" as a universal rule. On acceptance, update that guidance to reference
  this ADR's per-repository table so agents do not get conflicting instructions
  for trunk-only repositories. This separate meta-workspace change is not made
  while the ADR remains proposed.
- Promotion from `next` to `main` is a publication trigger for class-1 deploy
  repositories; the live tag-trigger exceptions above remain under review. For
  other classes the merge validates but does not mint a release (consistent
  with ADR-0007).

## Alternatives considered

- **One model for all repos (`next` → `main` everywhere).** Rejected: forces an
  integration branch onto single-maintainer, low-churn plugins where it only adds
  ceremony, and onto `.github` where there is nothing to integrate.
- **Trunk-only everywhere.** Rejected: the continuously deployed repos benefit
  from a staging branch before a change goes live, and `zi`'s scale warrants an
  integration buffer.
- **Leave it per-repo and informal.** Rejected: that is the status quo that let
  the catalog drift and required a manual remote audit to identify.

## References

- `decisions/0007-release-publication-flow.md` — repository classes this builds on.
- `decisions/0003-conventional-commits.md` — commit/branch naming conventions.
- [Issue #454](https://github.com/z-shell/.github/issues/454) — dated live audit
  and maintainer decision record.
