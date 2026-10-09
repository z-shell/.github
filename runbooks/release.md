<!-- GENERATED from knowledge/domains/governance/release.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

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

- validate pull requests into `main` and the merged `main` commit
- deploy according to the repository's existing delivery model
- do **not** force tag-driven changelog or release-please workflows onto these repositories unless the repository gains a separate packaged release artifact

### 2. Versioned tools and packages

Examples likely to fit:

- `zunit`
- `zsh-lint`
- `zpmod`

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
- for Zi only, follow ADR-0039: integrate qualified ordinary PRs on protected
  main, then separately review the exact current-main release plan and authorize
  a signed annotated milestone tag; ordinary merges do not publish releases

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

## Branch integration and publication

ADR-0019 separates code integration from publication:

- class-1 repositories integrate on `main` and deploy through their existing
  deployment workflow and environment controls;
- class-2 repositories integrate on `main`, then publish only an explicitly
  reviewed and tested `vX.Y.Z` tag;
- class-3 and class-4 repositories integrate on `main` unless an accepted ADR
  names a persistent integration exception; and
- `zi` follows protected-main integration under ADR-0039, with full stable
  qualification before merge and separately authorized signed milestones.

Preserve historical Zi promotion ancestry and tags. Repair or revert through
reviewed protected-main topic PRs; do not reset or force-push stable history.
Reintroducing a persistent integration branch requires a separate ADR decision.

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
publishing, so the class-2 publication boundary is unchanged.

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
- Do **not** add this to class-1, class-3, or class-4 repositories.

## Zi signed milestones

[ADR-0039](../decisions/0039-zi-main-integration-and-signed-milestones.md) replaces the historical Zi promotion exception. Ordinary work targets protected `main`; every merge is immediately consumable through the existing installation and self-update channels. Require the full Zsh matrix, ZD compatibility, full Trunk and CodeQL checks, clean startup and real-object lifecycle qualification before merge. A failed, cancelled or skipped constituent fails the aggregate gate.

Ordinary merges do not publish milestones. Review `scripts/release-plan.zsh` output for the full SHA on current protected `main`, including its semantic version and deterministic notes, then separately authorize and push a signed annotated tag for that SHA. The existing tag-driven verifier and publisher check the signature, current-main target, complete exact-SHA post-merge workflow allowlist and semantic version, and preserve idempotency and tag-conflict rejection. A no-op plan creates no tag or release. No signing key is stored in Actions and no proposal issue is required for every merge.

Protected tag creation is limited to the existing administrator role; update and deletion protections remain. That administrative capability is not authorization to move an existing tag. Read the live tag rules before publication and obtain authorization for the exact version, notes and SHA.

### Historical promotion contract

Before the ADR-0039 cutover, ADR-0028 coupled reviewed next-to-main promotion to automatic milestone publication after exact-SHA validation. That publisher, source guard and promotion-only issue closure are retired. Keep [ADR-0028](../decisions/0028-zi-promotion-is-release-authorization.md), existing tags and promotion merge ancestry as history, and retain [Zi's migration evidence](https://github.com/z-shell/zi/blob/main/docs/MAIN_MIGRATION.md). Remote next retirement remains a separately authorized cleanup step after downstream references and retained work are accounted for.

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
