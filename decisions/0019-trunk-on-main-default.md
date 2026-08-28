# 19. Trunk-on-Main Default with a Zi Integration Exception

- **Status:** ACCEPTED
- **Date:** 2026-08-28
- **Deciders:** ss-o
- **Supersedes:** `decisions/0008-branching-model.md`,
  `decisions/0016-promotion-trigger-criteria.md`
- **Superseded by:** None

## Context

ADR-0008 assigned persistent `next` branches to `wiki`, `src`, `zi`,
`zsh-lint`, and `zsh-eza`. ADR-0016 subsequently proposed promotion-readiness
automation for all five. Live workflow and branch-history evidence now shows
that a single integration-branch model does not match their delivery models:

- `wiki` and `src` deploy from `main`. Their persistent `next` branches add a
  second integration queue without providing an independently exercised
  staging environment.
- `zsh-lint` publishes immutable version tags. A persistent branch promotion
  is not the publication boundary; the reviewed and tested tag is.
- `zsh-eza` is consumed from Git and has the same validation on `main` and
  `next`. The second permanent branch adds promotion work without a distinct
  quality gate.
- `zi` has high change volume, direct Git consumers, and a dedicated promotion
  validation path. A maintained integration buffer remains useful there.

The old rules also combined two incompatible requirements. Squash or rebase
promotion creates commits on `main` that `next` does not contain, while linear
history forbids the merge commit that would preserve ancestry. Routine
back-merges or branch realignment then became mandatory administrative work.
That is a property of the model, not an occasional incident.

The decision was re-evaluated in
[z-shell/.github#550](https://github.com/z-shell/.github/issues/550).

## Decision

### Organization default

Use trunk-based development on `main` as the organization default:

- branch short-lived `feature-<id>`, `bug-<id>`, `hotfix-<id>`, and
  dependency-update branches from current `main`;
- open pull requests into `main`;
- require the repository's applicable tests and review controls before merge;
- prefer squash merge for ordinary short-lived topic branches;
- delete short-lived topic branches after merge; and
- keep deployment and publication controls separate from code integration.

`main` must remain releasable. This does not mean every merge publishes:

- class-1 repositories deploy from `main` through their existing deployment
  workflow and environment controls;
- class-2 repositories publish only from an explicitly reviewed `vX.Y.Z` tag;
- class-3 repositories may be consumed directly from `main`; and
- class-4 repositories integrate on `main` without an implied release.

The trunk-on-`main` repositories previously assigned `next` are:

| Repository | Class | Integration branch | Publication or consumption boundary |
| ---------- | ----- | ------------------ | ----------------------------------- |
| `wiki`     | 1     | `main`             | successful deployment from `main`   |
| `src`      | 1     | `main`             | successful deployment from `main`   |
| `zsh-lint` | 2     | `main`             | reviewed `vX.Y.Z` tag               |
| `zsh-eza`  | 3     | `main`             | `main` consumable ref               |

Existing work on `next` must be promoted or otherwise resolved before each
branch is retired. Deleting a persistent branch is the final migration step,
after workflow, dependency automation, documentation, open pull request, and
ruleset references have been moved to `main` and the retained history has been
verified.

### Approved persistent integration exception

`zi` retains `next` as its integration branch and `main` as its stable
consumable ref. This is a named exception, not a class-wide rule.

For `zi`:

- ordinary feature, fix, documentation, and dependency pull requests target
  `next`;
- promotion is a pull request from `next` to `main`;
- promotion uses **Create a merge commit**, never squash or rebase;
- `main` must not require linear history;
- `delete_branch_on_merge` remains disabled so GitHub does not remove `next`;
- the `main` ruleset or required CI must reject ordinary topic branches while
  allowing `next` and an explicitly reviewed `hotfix-*` branch; and
- a successful promotion needs no routine back-merge because the merge commit
  makes the promoted `next` commit an ancestor of `main`.

A critical hotfix may branch from `main` and merge to `main`. It must then be
merged into `next` with an ancestry-preserving merge commit before normal
development continues. This is incident-specific synchronization, not routine
post-promotion reconciliation.

Any future persistent integration branch requires an explicit ADR amendment
that names the repository, explains the independent gate or integration need,
defines its promotion method, and records how ancestry is preserved.

## Migration

For each repository moving to trunk-on-`main`:

1. Inventory commits, trees, tags, open pull requests, automation, rulesets,
   and external branch references for `main` and `next`.
2. Promote or retarget every retained change from `next`.
3. Update workflows, dependency automation, contributor guidance, and links to
   use `main`.
4. Apply and verify the class-appropriate `main` ruleset and repository merge
   settings.
5. Verify required checks on a real pull request into `main`.
6. Verify `next` has no unique retained content and no open pull request still
   depends on it.
7. Delete the remote `next` branch and re-audit repository settings.

For `zi`, update protection and documentation to the ancestry-preserving
promotion contract above, then validate it on the next real promotion.

## Consequences

### Positive

- Four repositories lose a redundant permanent queue and its promotion delay.
- Class-2 integration aligns with its actual tag publication boundary.
- Deploy repositories validate the exact branch that deploys.
- `zi` keeps the buffer its delivery and change profile justify.
- Merge ancestry replaces routine reconciliation for the retained exception.
- New repositories have one default model and an explicit exception process.

### Costs and risks

- Migration requires coordinated workflow, ruleset, dependency automation,
  documentation, and branch-reference changes.
- Direct-to-`main` integration increases the importance of fast required CI,
  small pull requests, and deployment rollback controls.
- `zi` history includes promotion merge commits and therefore cannot be fully
  linear on `main`.
- Removing `next` can disrupt stale clones or undocumented external links, so
  deletion must follow the recorded reference audit.

## Alternatives considered

- **Keep `next` in all five repositories.** Rejected because four repositories
  have no independent gate that justifies the ongoing promotion and
  reconciliation cost.
- **Move every repository to trunk-on-`main`.** Rejected because `zi` has a
  useful, exercised promotion boundary for a high-change Git-consumed core.
- **Keep squash promotion plus routine back-merge.** Rejected because it
  manufactures divergence and turns every promotion into two coordinated
  changes.
- **Require linear history everywhere.** Rejected for persistent integration
  branches because it forbids the merge commit needed to preserve ancestry.

## References

- `decisions/0007-release-publication-flow.md`
- `decisions/0013-repository-settings-baseline.md`
- `runbooks/branch-protection.md`
- `runbooks/dependency-management.md`
- `runbooks/new-repository.md`
- `runbooks/release.md`
- [z-shell/.github#550](https://github.com/z-shell/.github/issues/550)
- [GitHub flow](https://docs.github.com/en/get-started/using-github/github-flow)
- [Configuring pull request merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges)
- [About rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
- [Managing deployment environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
