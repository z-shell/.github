# 3. Adopt Conventional Commits across z-shell repositories

- **Status:** PROPOSED
- **Date:** 2026-05-19
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

The organization maintains many repositories with inconsistent commit-message and pull-request title styles.

That inconsistency makes several jobs harder:

- release-note generation
- cross-repo impact analysis
- review of what changed since a tag or milestone
- consistent machine-readable history for tooling and LLM agents

Conventional Commits is a widely supported standard that solves the history-format problem. Release automation can then be layered on selectively where it genuinely fits the repository's publication model.

## Decision

Adopt Conventional Commits as the canonical commit-message and PR-title format across z-shell repositories.

Recommended form:

```text
<type>(<scope>): <short description>
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `chore`
- `refactor`
- `test`
- `build`
- `ci`
- `perf`
- `style`
- `revert`

`scope` is optional but encouraged in larger repositories such as `zi`.

Breaking changes use either:

```text
feat!: change the public behavior
```

or:

```text
feat(scope): change the public behavior

BREAKING CHANGE: explanation
```

## Release automation policy

Conventional Commits is org-wide. Release automation is **repo-type-aware**, not universal.

- **Versioned tools and packages** may adopt release automation such as `release-please` when semantic tags are the publication boundary.
- **Continuously deployed repositories** such as hosted docs or images should keep deployment and release policy aligned with their existing delivery model instead of forcing tag-driven release tooling.
- **Meta and infrastructure repositories** such as `.github` should adopt Conventional Commits for history quality, but should not add release automation unless they gain a user-facing packaged artifact that benefits from it.

## Rollout

1. Pilot Conventional Commits enforcement in active repositories where maintainers want cleaner history immediately.
2. Pilot release automation only in repositories whose release model benefits from semantic tags and generated changelogs.
3. Expand incrementally as repositories are actively maintained.
4. Do not churn quiet, stable repositories just to standardize tooling.

## Consequences

### Positive

- Consistent, machine-readable history across the organization
- Easier changelog, release, and cross-repo analysis
- Better guidance for contributors and LLM agents
- Release automation can be introduced where it creates real leverage

### Negative / costs

- Contributors need to learn a small formatting convention.
- PR-title validation may initially feel stricter than the current workflow.
- Selective automation requires maintainers to classify repositories by release model instead of assuming one size fits all.

### Neutral

- This does not rewrite history.
- This does not require every repository to adopt release automation.

## Alternatives considered

1. **Status quo:** rejected because inconsistent history is already a maintenance cost.
2. **Conventional Commits plus universal release automation:** rejected because not every z-shell repository releases via semantic tags.
3. **Custom commit convention:** rejected because Conventional Commits has the best ecosystem support.

## References

- <https://www.conventionalcommits.org/>
- `AGENTS.md`
