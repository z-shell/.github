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

1. `src` and `zsh-eza` both had `renovate.json` with no `baseBranches`
   override. Renovate defaulted to the repository's default branch (`main`),
   opening routine dependency-update PRs that bypassed `next` entirely. Over
   time, enough of these (plus a few manually-merged feature branches) landed
   directly on `main` to diverge it from `next` by more than a dozen commits
   in `zsh-eza`'s case, with real merge conflicts to resolve before `next`
   could be promoted again. `dependency-management.md` already documents the
   `baseBranches` override as an example — the actual gap was that nothing
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
      This is the single highest-value check in this runbook — it is the one
      that caused actual data loss (recovered from the merge commit's known
      SHA in this case, but that is luck, not a safety net).
- [ ] **`renovate.json` has `"baseBranches": ["next"]`** if the repository
      uses Renovate. See `dependency-management.md` for the full config
      example. Check `.github/dependabot.yml`'s `target-branch` too — it is
      easy to fix Dependabot's target and assume Renovate inherited the same
      fix; they are independent configs.
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
      (a single `run:` step reading `github.head_ref`, no third-party
      actions needed). The check must run at least once on a real PR against
      `main` before GitHub will accept its context name in
      `required_status_checks`.

## Squash-merge trailers

When squash-merging a `next` → `main` promotion PR without an explicit
`--body`, GitHub synthesizes one by aggregating the squashed commits'
trailers — which reliably reintroduces `Co-authored-by` and `Signed-off-by`
trailers even when no individual commit you authored had one. Only
`Co-authored-by` is organization-disallowed (`AGENTS.md`); letting a
synthesized body reintroduce it violates that policy regardless of which
squashed commit it came from. Always pass both `--subject` and an explicit
one-line `--body` (e.g. `gh pr merge <n> --squash --subject "..." --body "..."`) to suppress
the synthesized body. Verify with
`gh api repos/<org>/<repo>/commits/<sha> --jq .commit.message` before
considering the promotion done.

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
