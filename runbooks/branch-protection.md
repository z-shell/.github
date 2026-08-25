# Runbook — Branch Protection for `next` → `main` Repositories

Use this runbook when provisioning or auditing branch rulesets and repository
settings for a repository that uses the `next` → `main` branch model
(`decisions/0008-branching-model.md`). It exists because `z-shell/src` and
`z-shell/zsh-eza` were both found, independently, with the same three gaps
during an audit — none of them were visible from the ruleset UI alone.

## Why this exists

A repository can have a correctly configured `main`/`next` ruleset pair and
still let `main` and `next` diverge, or lose the `next` branch outright,
because the gaps are in _repository settings_ and _automation defaults_ that
rulesets do not cover. Two incidents motivated this runbook:

1. `src` and `zsh-eza` both had repository config with no `baseBranchPatterns`
   override. Renovate defaulted to the repository's default branch (`main`),
   opening routine dependency-update PRs that bypassed `next` entirely. Over
   time, enough of these (plus a few manually-merged feature branches) landed
   directly on `main` to diverge it from `next` by more than a dozen commits
   in `zsh-eza`'s case, with real merge conflicts to resolve before `next`
   could be promoted again. `dependency-management.md` already documents the
   `baseBranchPatterns` override as an example. The actual gap was that nothing
   audited whether a `next`-model repository had actually applied it.
2. Promoting `zsh-eza`'s `next` into `main` via a PR merge (`next` as the PR's
   head branch) triggered GitHub's "Automatically delete head branches" repo
   setting, which deleted `next` — the repository's persistent development
   branch, not a disposable feature branch — immediately after the merge.
   **The ruleset's `deletion` rule did not stop this.** The merge itself ran
   under an organization-admin ruleset bypass (needed because the sole
   `CODEOWNERS` entry was also the PR author, so the required code-owner
   review could never be satisfied by anyone else), and the automatic
   post-merge deletion inherited that same bypass context.

## Checklist

Run every item below for a repository whose `decisions/0008-branching-model.md`
row is `next` → `main`. Skip repositories that are trunk-on-`main`.

- [ ] **`delete_branch_on_merge` is `false` at the repository level.**
      `gh api repos/<org>/<repo> --jq .delete_branch_on_merge`. If `true`,
      any PR that uses `next` as its head branch (i.e. every `next` → `main`
      promotion) risks GitHub deleting `next` right after merge, regardless of
      the ruleset's `deletion` rule. Disable it:
      `gh api -X PATCH repos/<org>/<repo> --field delete_branch_on_merge=false`.
      Keep this setting disabled as the required baseline for ordinary pull
      request merges. It is not a complete safeguard for GitHub's asynchronous
      stacked-merge path; see the caveat below.
- [ ] **`.github/renovate.json` has `"baseBranchPatterns": ["next"]`** if the
      repository uses Renovate. See `dependency-management.md` for the full
      config example. Check `.github/dependabot.yml`'s `target-branch` too:
      it is easy to fix Dependabot's target and assume Renovate inherited the
      same fix; they are independent configs. A repository with **no**
      Renovate config still needs `dependabot.yml`'s `target-branch` set for
      every ecosystem it configures — an update block without one silently
      targets the default branch (`zi#384`).
- [ ] **`main` and `next` are each governed by exactly one Repository Ruleset**,
      not a mix of a ruleset and legacy classic branch protection. Classic
      protection and rulesets both apply when both are present, and their
      settings can silently contradict each other (observed: classic
      protection allowing force-pushes while the ruleset's `non_fast_forward`
      rule blocked them — harmless only because the stricter rule wins, but
      confusing to audit and a sign the branch was migrated incompletely).
      List them with `gh api repos/<org>/<repo>/rulesets`; check for lingering
      classic protection with `gh api repos/<org>/<repo>/branches/<branch>/protection`
      (a `404` means none exists, which is correct).
- [ ] **A required status check blocks PRs into `main` whose head is not
      `next` or `hotfix-*`.** Rulesets have no native "restrict PR source
      branch" condition, so this has to be a CI check wired in as
      `required_status_checks`. See `.github/workflows/main-branch-guard.yml`
      in `z-shell/src` or `z-shell/zsh-eza` for the reference implementation
      (a single `run:` step, no third-party actions needed). The check must
      first require `github.event.pull_request.head.repo.full_name` to equal
      `github.repository`, because a fork can reuse an allowed branch name.
      It can then allow only `github.head_ref == 'next'` or
      `github.head_ref` matching `hotfix-*`. The check must run at least once
      on a real PR against `main` before GitHub will accept its context name
      in `required_status_checks`.

## Asynchronous stacked-merge caveat

GitHub's asynchronous stacked-merge path has one observed exception to the
normal branch-deletion setting. During
[`z-shell/zsh-lint#117`](https://github.com/z-shell/zsh-lint/pull/117), the
accepted asynchronous merge deleted persistent head branch `next` even though
`delete_branch_on_merge` was `false`. GitHub also retargeted
[`dependent PR #110`](https://github.com/z-shell/zsh-lint/pull/110) from `next` to `main` and
placed it in immutable stack metadata. Treat this as evidence for that path,
not proof that every asynchronous merge behaves identically.

Before using an asynchronous stacked merge for a persistent branch:

1. Record the promotion pull request's exact head branch and head SHA.
2. Record each dependent pull request's base branch, base SHA, head branch,
   and head SHA.
3. After the merge, immediately verify that the persistent head ref still
   exists and that dependent pull requests retain their intended bases.

If GitHub removes the branch, stop further merges. With explicit maintainer
authorization, recreate only the recorded branch ref at the recorded exact
head SHA, then re-audit every dependent pull request. GitHub may reject a base
restoration after it creates immutable stack metadata, so do not assume the
original base can be restored. Record and obtain an explicit maintainer
decision for any dependent pull request that must remain retargeted.

## Squash-merge trailers

`AGENTS.md` does not ban `Co-authored-by` trailers outright. A trailer
crediting a real human — including the PR author crediting themselves via a
GitHub-synthesized trailer — is fine. The ban is specifically on crediting a
**bot, AI agent, or automation** as a co-author (for example a coding
assistant's default identity, or a `[bot]` GitHub account); those must never
appear regardless of merge method.

When squash-merging a PR without an explicit `--body`, GitHub synthesizes
one by aggregating the squashed commits' trailers, which can carry forward
a bot/agent `Co-authored-by` from an individual commit even when the PR
subject and description don't mention one. Separately — confirmed
empirically on `z-shell/.github#519` — GitHub appends a `Co-authored-by`
trailer for the merger even with the repository's
`squash_merge_commit_message` set to `BLANK` and an otherwise-empty default
body (`decisions/0013-repository-settings-baseline.md`); that setting
reduces the aggregation risk but does not eliminate this second, apparently
independent mechanism. Neither is a problem when the credited party is the
human author/merger. It is a problem if any commit in the PR carries a
bot/agent trailer, since squash synthesis can promote it into the merge
commit. Always pass both `--subject` and an explicit one-line `--body`
(e.g. `gh pr merge <n> --squash --subject "..." --body "..."`) when that
risk exists, and verify with
`gh api repos/<org>/<repo>/commits/<sha> --jq .commit.message` before
considering the promotion done.

## Post-promotion reconciliation

A squash merge keeps `main` linear but creates a new commit that is not in
`next`, even when the resulting branch trees are identical. If that commit is
not merged back, the next promotion uses an older merge base and can show
already-promoted changes or produce avoidable conflicts.

Immediately after a successful squash promotion:

1. Fetch the current `main` and `next`, then verify the promoted `main` tree
   matches the reviewed `next` tree:

   ```bash
   git fetch origin main next
   git diff --exit-code origin/main origin/next
   ```

2. Create the signed merge commit on an issue branch from the current `next`
   and verify it preserves the pre-merge `next` tree:

   ```bash
   next_tree=$(git rev-parse 'origin/next^{tree}')
   git switch -c <issue-branch> origin/next
   git merge --no-ff -S origin/main \
     -m "chore: reconcile promoted main into next (#<issue>)"
   test "$(git rev-parse 'HEAD^{tree}')" = "$next_tree"
   git push -u origin <issue-branch>
   ```

   Open a PR from `<issue-branch>` into `next`. Merge it with **Create a merge
   commit** so the `main` parent remains in history. Do not squash or rebase
   this reconciliation PR.

3. Fetch both branches again and verify `main` is now an ancestor of `next`:

   ```bash
   git fetch origin main next
   git merge-base --is-ancestor origin/main origin/next
   ```

Do not reset, rebase, force-push, or replace the persistent `next` branch to
perform this reconciliation. If the branch trees differ before the back-merge,
stop and review the delta instead of resolving it as an ancestry-only change.

## Reference ruleset shape

Both `main` and `next` should be a single Repository Ruleset each, scoped by
`refs/heads/<branch>`, with `bypass_actors` granting `OrganizationAdmin` and
the repository's admin/maintain/write roles `bypass_mode: always` (self-review
deadlock is expected and intentional: the only `CODEOWNERS` entry is often
also the person merging, so bypass is how promotions and fixes actually land;
`gh pr merge --admin` is the normal path here, not an escape hatch).

`main`: `deletion`, `required_linear_history`, `pull_request` (code-owner
review required, approving-review count `0`), `non_fast_forward`,
`copilot_code_review`, `required_status_checks` (the guard workflow above).

`next`: `deletion`, `non_fast_forward`, `required_signatures`, `pull_request`.
`required_linear_history` is deliberately absent from `next` — ordinary merge
commits (not squashes) are the convention for feature/fix PRs landing there.

## See also

- `decisions/0008-branching-model.md`
- `runbooks/dependency-management.md`
- `runbooks/new-repository.md`
