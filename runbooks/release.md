# Runbook — Release coordination

Use this runbook to decide whether a repository should adopt release automation and to coordinate releases without forcing one model onto every z-shell repository.

> This runbook implements the decision recorded in
> [`decisions/0007-release-publication-flow.md`](../decisions/0007-release-publication-flow.md)
> (**ACCEPTED**): semantic tags `vX.Y.Z` are the publication boundary for
> versioned tools/packages, released via the simple tag-driven `zunit` pattern
> (not `release-please`). The repo classes below are the authoritative reference.

## Release coordination guidance

1. Conventional Commits are the proposed default history format until the corresponding ADR is accepted.
2. Release automation is **repo-type-aware**, not universal.
3. Do not add `release-please` to a repository just because it exists elsewhere.

## Repository classes

### 1. Continuously deployed artifacts

Examples:

- `wiki`
- `src`
- `zd` image workflows

Policy:

- validate continuously on the development branch
- deploy according to the repository's existing delivery model
- do **not** force tag-driven changelog or release-please workflows onto these repositories unless the repository gains a separate packaged release artifact

### 2. Versioned tools and packages

Examples likely to fit:

- `zunit`
- `zsh-lint`

Policy:

- use Conventional Commits
- semantic tags are the publication boundary
- these repositories are candidates for release automation such as `release-please`

### 3. Git-consumed source repositories

Examples likely to fit:

- `zi`
- most plugins and annexes

Policy:

- use Conventional Commits for clean history and cross-repo reasoning
- keep CI focused on validation
- do **not** add release automation unless the repository later gains a separate packaged artifact or a clear tag-driven release workflow with maintainer buy-in

### 4. Meta and infrastructure repositories

Examples:

- `.github`

Policy:

- use Conventional Commits
- no release automation unless the repository gains a user-facing packaged artifact that benefits from it

## Suggested pilot set

Based on the current workspace and org policy, the safest first `release-please` pilot candidates are versioned tool repositories such as:

- `zunit`
- `zsh-lint`

Repositories that should stay out of the first pilot:

- `wiki`
- `.github`
- `zi`

## Post-promotion branch reconcile (class 1)

Applies to class-1 repositories that promote a development branch to a deployed
branch, such as `wiki` promoting `next` to `main`.

Branch names differ between repositories. The procedure below takes them as
`DEPLOY` and `DEV` variables — set them for the repository you are working on
rather than assuming `main` and `next`.

### Why this is routine, not an incident

When the deployed branch requires both pull requests and linear history, every
merge method GitHub offers — squash or rebase — creates **new commits on the
deployed branch that the development branch does not have**. A merge commit,
which would keep the branches related, is exactly what linear history forbids.

So the development branch diverges after *every* promotion, by construction.
There is no branch-protection configuration that avoids it. Reconciling is a
step in the release, not a sign that something went wrong.

### Do not reconcile with a merge

A `git merge` creates a merge commit, which violates `required_linear_history`.
An administrator's push is **not refused** — it prints `Bypassed rule
violations` and succeeds anyway. The push is not silent; it is simply not
stopped, and the warning is easy to miss. Check the branch's rules before
choosing a strategy:

```sh
gh api repos/OWNER/REPO/rules/branches/BRANCH -q '[.[].type]|join(", ")'
```

Note that rulesets and classic branch protection are **independent** systems and
the effective rule is their union. Classic protection can report
`required_linear_history: false` for a branch that a ruleset separately
enforces it on, so check both before concluding a merge commit is allowed.

### Procedure

Immediately after the promotion merges, when everything on the development
branch has shipped.

Save this as a script and run it — do not paste the lines individually. Steps 2
and 3 reset a branch and force-push it, so the safety gate has to be able to
abort the run, which it cannot do when each line is pasted separately.

```sh
#!/usr/bin/env sh
set -eu

# Branch names for the repository being reconciled.
DEPLOY=main
DEV=next

git fetch origin

# 1. Safety gate. The trees must be identical — that is what makes the reset
#    content-neutral. Differing trees mean the development branch carries work
#    the promotion did not include, so abort rather than destroy it.
if [ "$(git rev-parse "origin/$DEPLOY^{tree}")" != "$(git rev-parse "origin/$DEV^{tree}")" ]; then
  echo "STOP: $DEV has content not present in $DEPLOY; do not reset" >&2
  exit 1
fi

# 2. Realign the development branch onto the deployed branch.
git checkout "$DEV"
git reset --hard "origin/$DEPLOY"

# 3. Publish. A force is required: history is being replaced, not extended.
git push --force-with-lease "origin" "$DEV"
```

Use `--force-with-lease`, never `--force`, so the push aborts if anyone else
has pushed to the branch since the fetch.

### What to expect, and what to check

- **This push bypasses a rule and cannot avoid it.** A direct push carries no
  prior status check, so the branch reports
  `Required status check "Trunk Check" is expected`. There is no
  pull-request route to this operation — a pull request can only add commits,
  and realignment rewrites history. Read the push output rather than silencing
  it, and confirm the only bypass reported is the expected status check.
- **Never run `git push -q` or pipe push output through `tail` on a protected
  branch.** The `Bypassed rule violations` warning arrives at push time and is
  easily truncated away.
- Afterwards the two branches should be the *same commit*, not merely the same
  content:

  ```sh
  [ "$(git rev-parse "origin/$DEV")" = "$(git rev-parse "origin/$DEPLOY")" ] && echo reconciled
  ```

### If the safety gate fails

Do not reset. Differing trees mean the development branch carries work that the
promotion did not include. Promote that work first, or rebase it onto the
deployed branch, and only then realign.

## Release preparation automation (class 2)

The reusable workflow
[`release-prepare.yml`](../.github/workflows/release-prepare.yml) automates the
_preparation_ half of the class-2 flow without moving the publication boundary.
On every push to the default branch it:

1. computes the next semantic version from Conventional Commits since the last
   `vX.Y.Z` tag (`feat` → minor, `fix`/`perf` → patch, `!`/`BREAKING CHANGE` →
   major; no releasable commits → clean no-op)
2. drafts a changelog with GitHub Models (`actions/ai-inference`), degrading to
   a grouped commit list when inference is unavailable
3. opens or updates a single `release-proposal` issue containing the draft
   notes and the exact annotated-tag commands

The maintainer-pushed annotated tag remains the only publication act, and the
repository's tag-driven `release.yml` (zunit pattern) still does the
publishing, so ADR 0007 is unchanged.

Caller snippet for a class-2 repository:

```yaml
---
name: Release Prepare

on:
  push:
    branches: [main]

permissions:
  contents: read
  issues: write
  models: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: false

jobs:
  propose:
    uses: z-shell/.github/.github/workflows/release-prepare.yml@main
```

Notes:

- Callers own `concurrency`; the reusable workflow does not set it.
- `models: read` enables the GitHub Models changelog draft; without it the
  workflow still opens the proposal with the fallback commit list.
- Do **not** add this to class-1, class-3, or class-4 repositories — they have
  no tag boundary to prepare for.

## Release-automation decision checklist

Before proposing `release-please` for a repository, confirm:

1. The repo already uses semantic tags meaningfully.
2. A generated changelog would actually help maintainers and users.
3. The repo is not primarily consumed directly from Git `main` or `next`.
4. The release boundary is deliberate and not just "whatever is currently on the default branch".
5. Maintainers want the repo to publish from tags rather than from continuous deployment.

If any answer is "no", prefer Conventional Commits without release automation.

## Cross-repo breaking-change workflow

When `zi` or another core repo makes a breaking change:

1. identify the public contract that changed
2. search the organization for in-org consumers
3. list affected repositories and the likely adaptation work
4. draft, but do not apply, follow-up issues or PRs

## Prompt template — release classification

```text
Review z-shell/<repo> and classify its release model using the z-shell release runbook.

Answer:
1. Which repository class does it fit?
2. Should it use Conventional Commits only, or Conventional Commits plus release automation?
3. If release automation is appropriate, why?
4. If it is not appropriate, what is the correct publication model?

Draft only. Do not modify workflows.
```

## Prompt template — breaking-change coordination

```text
Read <issue or PR> describing a breaking change in z-shell/<repo>.

Search the z-shell organization for likely consumers of the changed API, behavior, or workflow.

Output:
- affected repositories
- likely impact
- proposed follow-up issue titles or PR scopes

Draft only. Do not act.
```

## See also

- `decisions/0003-conventional-commits.md`
- `runbooks/org-review.md`
- `runbooks/triage.md`
