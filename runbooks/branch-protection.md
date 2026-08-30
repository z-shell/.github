# Runbook: Persistent Integration Branch Protection

Use this runbook for a repository explicitly approved to retain a persistent
integration branch under
[`decisions/0019-trunk-on-main-default.md`](../decisions/0019-trunk-on-main-default.md).
The current and only approved repository is `z-shell/zi`, with `next` as the
integration branch and `main` as the stable consumable branch. Trunk-on-`main`
repositories do not use this runbook.

## Required repository settings

- `default_branch` is `main`.
- `allow_merge_commit` is `true`. Promotion requires a merge commit.
- `delete_branch_on_merge` is `false`. GitHub must not delete persistent
  `next` after promotion.
- Renovate `baseBranchPatterns` and every Dependabot `target-branch` point to
  `next`.
- `main` and `next` are each governed by one active repository ruleset. Remove
  overlapping classic branch protection after verifying the ruleset equivalent.

Rulesets and classic protection are independent and their requirements are
cumulative. Audit both before removing either one:

```sh
gh api repos/OWNER/REPO/rulesets
gh api repos/OWNER/REPO/branches/BRANCH/protection
```

A `404` from the second request means classic protection is absent.

## Required ruleset shape

`main`:

- block deletion and force pushes;
- require pull requests and the applicable status checks;
- require code-owner review when the repository can satisfy it;
- require the main-branch source guard described below;
- restrict the pull-request rule to merge commits; and
- **do not require linear history**.

`next`:

- block deletion and force pushes;
- require pull requests and the applicable status checks; and
- require signed commits when the repository's class baseline recommends it;
  and
- **do not require linear history**, because hotfix synchronization preserves
  the merge commit from `main`.

Bypass actors must be explicit and no broader than needed for documented
self-review deadlocks, incident recovery, or another reviewed administrative
operation. Record and inspect bypass output. A bypass is not evidence that a
required check passed.

## Main-branch source guard

Rulesets cannot restrict a pull request by head branch. A required workflow
must reject pull requests into `main` unless:

1. `github.event.pull_request.head.repo.full_name == github.repository`; and
2. the head is exactly `next`, or matches an explicitly reviewed `hotfix-*`
   branch.

Checking repository identity first prevents a fork from reusing an allowed
branch name. Run the guard on a real pull request before adding its context to
`required_status_checks`, because GitHub only accepts observed check contexts.

## Promotion procedure

Promotion preserves Git ancestry. Never squash or rebase a persistent branch
into its stable branch.

1. Fetch both remote branches and verify that the stable branch carries no
   content the candidate lacks. This proves that no hotfix or other
   stable-only commit was omitted:

   ```sh
   git fetch origin main next
   test -z "$(git diff --name-only origin/next...origin/main)"
   git log --left-right --graph --oneline origin/main...origin/next
   ```

   Do **not** test `git merge-base --is-ancestor origin/main origin/next`. That
   check cannot pass after a successful promotion and does not mean the branches
   have diverged in content. Promotion creates a merge commit on `main`, and
   that commit never exists on `next`, so `main` stops being an ancestor of
   `next` the moment a promotion lands. Treating the failure as drift produces a
   no-content reconciliation merge before every promotion, which is exactly the
   routine back-merge ADR-0019 removed.

   The empty three-dot diff is the real precondition: it is satisfied both
   immediately after a promotion and after ordinary work continues on `next`,
   and it still fails when a genuine stable-only commit, such as an unmerged
   hotfix, exists on `main`. When it fails, inspect
   `git log --oneline origin/next..origin/main` to identify the omitted commit
   and merge it forward through the hotfix synchronization procedure below.

2. Open or update a pull request with base `main`, head `next`, and a
   Conventional Commit title such as `chore: promote next to main`.
3. Require the full promotion check set on the exact head SHA. Re-run stale or
   cancelled checks rather than relying on an earlier commit.
4. Review the commit and file delta, deployment or consumer impact, and open
   blocking issues.
5. Immediately before merge, fetch again and record the reviewed `main` and
   `next` SHAs. Merge using **Create a merge commit**. Do not select squash or
   rebase.
6. Fetch again and verify that `main` is a merge commit, the reviewed `next`
   SHA is one of its parents, and the ancestry relationship holds:

   ```sh
   git fetch origin main next
   reviewed_main=<recorded-main-sha>
   reviewed_next=<recorded-next-sha>
   test "$(git rev-list --parents -n 1 origin/main | awk '{ print NF - 1 }')" -eq 2
   test "$(git rev-parse 'origin/main^1')" = "$reviewed_main"
   test "$(git rev-parse 'origin/main^2')" = "$reviewed_next"
   git merge-base --is-ancestor origin/next origin/main
   git branch -r --contains origin/next
   ```

7. Verify `next` still exists and repository settings still report
   `delete_branch_on_merge: false`.

A successful promotion does not need a back-merge. The promotion merge commit
contains the exact `next` head as a parent, so future work remains related to
`main` by construction.

## Hotfix synchronization

A critical fix may branch from current `main` as `hotfix-<id>` and merge into
`main` after the incident's required review and checks. Before ordinary work
continues, synchronize it into `next`:

1. create an issue branch from current `next`;
2. merge current `main` into that branch with a signed merge commit;
3. open a pull request into `next` and preserve the merge commit; and
4. verify `git merge-base --is-ancestor origin/main origin/next` after merge.

This is the one direction in which the ancestor test is correct, because
synchronization merges `main` into `next` and preserves the merge commit. It is
the mirror image of the promotion precondition, where the same test is wrong.
Keep the two straight: synchronization makes `main` an ancestor of `next`, and
promotion makes `next` an ancestor of `main`. Neither relationship survives in
both directions at once.

Do not reset, rebase, or force-push the persistent branch to synchronize a
hotfix. If the trees conflict, resolve them in the reviewed synchronization
pull request and run the full `next` validation set.

## Asynchronous stacked-merge caveat

GitHub's asynchronous stacked-merge path has previously deleted persistent
`next` even with `delete_branch_on_merge: false`, and retargeted a dependent
pull request into immutable stack metadata. Avoid that path for a persistent
branch promotion.

If it is unavoidable, record the promotion head name and SHA plus every
dependent pull request's base and head before merge. Verify them immediately
afterward. If GitHub removes the branch, stop further merges. Recreating the
recorded ref or changing a dependent pull request requires a separately
reviewed recovery decision using the recorded SHAs.

## Squash-merge trailers for topic branches

Squash merges remain suitable for short-lived topic branches. Pass explicit
`--subject` and `--body` values when merging with `gh` if any source commit may
carry an unwanted trailer. Verify the resulting message. A `Co-authored-by`
trailer may credit a real human, but must never credit a bot, AI agent, or
automation.

This section does not apply to `next` to `main` promotion, which must use a
merge commit.

## Audit evidence

Record at minimum:

- repository settings for default branch, merge methods, and branch deletion;
- complete ruleset details and any classic protection for both branches;
- dependency automation target branches;
- source-guard workflow and observed required context;
- promotion pull request head SHA and merge method; and
- post-merge ancestry and branch-existence checks.

## See also

- `decisions/0019-trunk-on-main-default.md`
- `decisions/0013-repository-settings-baseline.md`
- `runbooks/dependency-management.md`
- `runbooks/new-repository.md`
- `runbooks/release.md`
