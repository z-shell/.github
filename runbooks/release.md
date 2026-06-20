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
