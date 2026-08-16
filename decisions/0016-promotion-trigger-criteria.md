# 16. Next-to-Main Promotion Trigger Criteria

- **Status:** ACCEPTED
- **Date:** 2026-08-16
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

`decisions/0008-branching-model.md` establishes which repositories use the
`next` → `main` branch model (`wiki`, `src`, `zi`, `zsh-lint`, `zsh-eza`) and
states that promotion is a publication trigger for class-1 deploy repos.
`runbooks/branch-protection.md` and `runbooks/release.md` cover how a
promotion is protected (rulesets, `delete_branch_on_merge`, the main-branch
guard) and how it is reconciled afterward (the mandatory back-merge). None of
those documents states **when** a promotion should happen. That decision is
currently pure maintainer judgment, undocumented and unaudited — a gap
identified in [z-shell/.github#513](https://github.com/z-shell/.github/issues/513).

A working precedent already exists for automating a readiness *signal*
without automating the merge decision itself: `release-prepare.yml`
(class 2, ADR-0007) opens or updates a proposal issue with a draft changelog
when releasable commits land on the default branch, but a maintainer still
pushes the annotated tag that actually publishes. The same "propose, don't
merge" shape is the natural fit for `next` → `main` promotion, since ADR-0008
already treats promotion as a deliberate publication act, not a
side-effect of CI going green.

The five `next` → `main` repositories do not share the same cost of staleness
or the same blast radius from a bad promotion:

- `wiki`, `src` (class 1, deploy): a promotion triggers a deploy. A bad
  promotion is user-visible immediately.
- `zi`, `zsh-eza` (class 3, consumable ref): `main` is the ref consumers pull
  directly. Staleness has a direct, ongoing cost; there is no deploy step to
  protect against.
- `zsh-lint` (class 2): `next` feeds a `vX.Y.Z` release tag, and
  `release-prepare.yml` already computes readiness for that tag from commits
  on the default branch.

A single trigger rule for all five would either under-protect the deploy
repos or over-delay the consumable-ref repos.

## Decision

Adopt **readiness-proposal automation** as the default promotion-trigger
mechanism for every `next` → `main` repository, implemented as a reusable
`promote-prepare.yml` workflow (mirrors `release-prepare.yml`'s shape):

- On a trigger the caller repository chooses (push to the development branch,
  or a schedule), the workflow checks whether the development branch is ahead
  of the deployed branch, whether it has been green for the repository's
  configured bake window, and whether any open issue carries the
  `status:blocked` label (reused from the existing triage taxonomy —
  `lib/labels.yml` — rather than adding a new label).
- If all three conditions hold, it opens or updates a single
  development-branch → deployed-branch pull request. It never merges. The PR
  body restates the `runbooks/branch-protection.md` merge requirements
  (explicit `--subject`/`--body` on the squash, verify the resulting commit
  message, run the post-promotion back-merge) so the human merging it has the
  checklist in front of them.
- A maintainer merges the PR through the existing documented path
  (`gh pr merge --admin`, since the sole `CODEOWNERS` entry is typically also
  the author — this mirrors the bypass pattern `branch-protection.md` already
  documents as normal, not an escape hatch).

### Per-repository bake window

The bake window is the only per-repository parameter; everything else about
the mechanism is uniform.

| Repo        | Class | Bake window | Rationale                                                        |
| ----------- | ----- | ----------- | ------------------------------------------------------------------ |
| `wiki`      | 1     | 2 hours     | Gives delayed CI/nightly checks a chance to fail before a deploy. |
| `src`       | 1     | 2 hours     | Same as `wiki`; installer/loader validation can be slow.          |
| `zi`        | 3     | 0 (none)    | `main` is the consumable ref; staleness costs consumers directly. |
| `zsh-eza`   | 3     | 0 (none)    | Same rationale as `zi`.                                            |
| `zsh-lint`  | 2     | 0 (none)    | Readiness already gated by `release-prepare.yml`'s own signal.    |

These are starting values, not load-bearing constants — a maintainer can tune
a given repository's bake window without amending this ADR, the same way
`runbooks/branch-protection.md`'s checklist items are tunable enforcement
detail under ADR-0008's table.

## Consequences

- Every `next` → `main` repository gets a documented, auditable answer to
  "why hasn't this been promoted yet" instead of relying on someone noticing.
- The publication boundary stays a deliberate human act (a merge), consistent
  with ADR-0008; no repository auto-merges into `main`.
- `status:blocked` gains a second meaning in practice (general triage hold,
  and now promotion hold). If that overloading proves confusing in practice,
  a dedicated label can be introduced later without changing this ADR's
  mechanism.
- `wiki` and `src` gain a 2-hour minimum lag between "`next` is ready" and
  "a promotion PR exists." That is a deliberate cost traded for catching
  delayed CI failures before they deploy.
- This does not change ADR-0008's per-repository branch-model table, only
  which of those repositories' promotions get an automated readiness signal.

## Alternatives considered

- **Continuous promotion on every green commit.** Rejected as the default:
  no margin for delayed/nightly failures on `wiki`/`src`, where a bad
  promotion is immediately user-visible.
- **Fixed cadence (daily/weekly) for all five repos.** Rejected: a poor fit
  for `zi`/`zsh-eza`, where consumers pull `main` directly and a week of
  staleness has a real, ongoing cost with no compensating safety benefit.
- **One org-wide bake window instead of per-repo.** Rejected: applying the
  deploy repos' 2-hour window to `zi`/`zsh-eza` would add pure latency with
  no corresponding risk to protect against, since those repos have no deploy
  step.
- **Leave it fully manual (status quo).** Rejected: this is the gap
  `z-shell/.github#513` identified — it does not scale and is not auditable.

## References

- `decisions/0008-branching-model.md` — branch model and publication-trigger
  language this decision narrows.
- `decisions/0007-release-publication-flow.md` — the readiness-proposal
  precedent (`release-prepare.yml`).
- `runbooks/branch-protection.md` — merge mechanics the promotion PR body
  must restate (squash trailers, admin-bypass path, post-promotion reconcile).
- `runbooks/release.md` — `release-prepare.yml` reference implementation.
- `lib/labels.yml` — `status:blocked`, reused rather than duplicated.
- [z-shell/.github#513](https://github.com/z-shell/.github/issues/513) — the
  issue this ADR resolves.
- `.github/workflows/promote-prepare.yml` — draft reference implementation
  (PoC, not yet called by any repository).
