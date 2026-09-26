# Runbook: Pull requests

Use this runbook for every pull request to a z-shell repository, whoever opens it: a maintainer, a contributor, or an agent. It collects in one place the steps that are otherwise spread across `AGENTS.md`, [ADR-0003](../decisions/0003-conventional-commits.md), [ADR-0022](../decisions/0022-issue-traceability-on-pull-requests.md), [ADR-0026](../decisions/0026-review-triggers-and-fallback.md), [`branch-protection.md`](branch-protection.md), and `.github/workflows/commit-lint.yml`. Where this runbook and one of those disagree, the ADR or the workflow wins; fix the runbook. One interim exception: until the ADR-0026 amendment lands, the maintainer decision recorded on [#664](https://github.com/z-shell/.github/issues/664) also governs fallback reviews, and section 3 follows it where it extends ADR-0026.

## 1. Before the branch

- Read the owning issue and its acceptance criteria. The pull request is measured against them.
- Name the branch before creating it. The pattern is the `BRANCH_PATTERN` default in `.github/workflows/commit-lint.yml`:
  - `feature-<issue>`, `bug-<issue>` or `hotfix-<issue>`, optionally followed by `-<slug>` (for example `bug-480` or `feature-668-pull-requests`);
  - or `<type>/<slug>` with a slash after a Conventional Commits type (for example `docs/pull-requests-runbook`). `docs-488` matches neither and fails the required check.
- A repository may be stricter; its `AGENTS.md` says so (z-shell/F-Sy-H accepts only `feature|bug|hotfix-<issue>`).
- Branch from the repository's base: `main`, except `next` for z-shell/zi ([ADR-0019](../decisions/0019-trunk-on-main-default.md), [`branch-protection.md`](branch-protection.md)). In zi a `hotfix-*` branch may start from and target `main`, and is then synchronized into `next` as [`branch-protection.md`](branch-protection.md) describes.

## 2. Opening

- Title and commits follow Conventional Commits ([ADR-0003](../decisions/0003-conventional-commits.md)): `type(scope): description`, with the description at most 72 characters, including an issue suffix such as `(#123)`.
- Fill in the repository's pull-request template (the organization default is Summary, Verification, Agent handoff).
- Reference the owning issue in the body ([ADR-0022](../decisions/0022-issue-traceability-on-pull-requests.md)). Use `Closes #N` only when this diff meets every acceptance criterion of #N. Otherwise use `Refs #N`, say which criteria remain, and open or update a follow-up issue.
- When the change departs from what the issue asked for, say so in the body and get the maintainer's agreement before merging. A departure hidden behind `Closes` closes the issue on criteria nobody agreed to.
- Every factual or causal claim in the change and the body is checked, or marked as not yet verified.
- Run the repository's own checks before asking for review, and put the commands and their results under Verification.

## 3. Review

Reviews follow [ADR-0026](../decisions/0026-review-triggers-and-fallback.md).

A repository's `AGENTS.md` may declare automation-only diff classes that need no review of record (ADR-0026 decision 4): gitlink pointer moves in a meta-workspace, the generated-fixture refreshes that go with them, and dependency bumps opened by Renovate or Dependabot. A pull request made only of a declared class skips the steps below. A pull request that touches anything else is reviewed.

1. When the head is ready (checks green, body complete), request Copilot once. Confirm the request by a `review_requested` event on the pull request's timeline. An empty `requested_reviewers` list in the API response means the request did not register.
2. If the request does not register, the pull request is blocked on quota, not ready. In a class 2, 3 or 4 repository (`lib/repository-classes.yml`) the maintainer may then decide to use the fallback instead of waiting; an agent does not take that decision on its own. Run `.github/skills/code-review/SKILL.md` against `.github/instructions/code-review-generic.instructions.md` on the current head. Post the result as a pull-request review with inline threads for its findings, opening with `Fallback review under ADR-0026: Copilot request not registered on <sha>`. The marker line without that review is not a review.
3. A maintainer may elect the fallback up front, without requesting Copilot, in classes 2 to 4. The review then opens with `Fallback review under ADR-0026: maintainer elected, no Copilot request on <sha>` and is executed the same way. This follows the maintainer decision recorded on #664; the ADR-0026 amendment is pending.
4. Class 1 repositories never use the fallback: they wait for Copilot or a second human.
5. Act on every review thread with a fix, or a reply saying why not. The ruleset requires resolved threads (`required_review_thread_resolution`, [ADR-0013](../decisions/0013-repository-settings-baseline.md)).
6. Batch the thread fixes and push them once before the next Copilot request; that is one round. After the second round in which Copilot raises only implementation-level or wording findings, the maintainer decides whether to defer the rest to an issue instead of requesting a third review.
7. Any push after a fallback review, a rebase included, voids it (#664). Post a new fallback review on the new head before merging.

## 4. Merge

- All required checks pass on the head, a review of record has posted, and no thread is unresolved. A fallback review of record must be on that same head (section 3, step 7).
- Short-lived topic branches usually squash-merge. Persistent-branch promotion, and a zi hotfix synchronization branch that carries a merge commit of `main` into `next`, use a merge commit so the ancestry survives ([`branch-protection.md`](branch-protection.md)). Pass `--match-head-commit <sha>` so a push between checking and merging fails the merge.
- For a squash merge, pass the message explicitly and check it, as [`branch-protection.md`](branch-protection.md) describes for trailers.
- When the body says `Closes #N`, re-check the criteria against the merged diff. If one is not met, reopen #N or open a follow-up at once.
- In zi, a pull request merged into `next` leaves its issue open, because GitHub closes issues only from the default branch. Close those issues by hand when `next` is promoted to `main`, not earlier (zi's `AGENTS.md`).

## 5. After merge

- Move the Project 28 item as [`project-tracker.md`](project-tracker.md) describes.
- File the follow-ups promised in the body or in review replies, and link them.
- Delete the branch and any local worktree only with the maintainer's authorization.

## See also

- [`triage.md`](triage.md), for the issue a pull request starts from.
- [`learning-capture.md`](learning-capture.md), for lessons a pull request teaches.
- #668, for why this runbook exists.
