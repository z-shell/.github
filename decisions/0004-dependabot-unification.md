# 4. Standardize on Dependabot for Dependency Management

- **Status:** ACCEPTED
- **Date:** 2026-05-20
- **Deciders:** ss-o, Gemini CLI
- **Supersedes:** None
- **Superseded by:** `decisions/0012-hybrid-dependency-management.md`

## Context

Managing dependencies across 96+ repositories in the z-shell organization was inconsistent. Repositories were using a mix of:

- **Renovate:** Used in `src` and `z-shell-dot-github`.
- **Dependabot:** Used in `wiki`, `zd`, `zi`, and others.
- **Manual updates:** Used in many smaller plugins and annexes.

This fragmentation led to:

- High maintenance overhead (managing multiple tool configurations).
- Inconsistent update schedules and PR volumes.
- Increased risk of missing security patches in repositories without automated tracking.
- Redundant CI noise from competing update tools.

Organization guidelines emphasize better reuse, better verification, and reducing architectural drift.

## Decision

Standardize exclusively on **GitHub native Dependabot** for dependency management across all organization repositories.

1. **Remove Renovate:** Delete all `renovate.json` and `renovate-config.json` files from the workspace.
2. **Universal Dependabot:** Deploy `dependabot.yml` to every repository in the organization.
3. **Canonical Schedule:** Align all updates to a weekly schedule (Monday 05:00 UTC for `npm`, 05:30 UTC for `github-actions`).
4. **Grouped Updates:** Use Dependabot groups (e.g., `github-actions`, `npm` packages) to minimize PR noise.
5. **Ecosystem Coverage:**
   - Always track `github-actions` at the root (`/`).
   - Track `npm` where a `package.json` exists.
   - Track other ecosystems (Go, Cargo, etc.) only where explicitly required by the repository's source.

## Consequences

### Positive

- **Simplicity:** Dependabot is built into GitHub, requiring no external service or PAT management.
- **Consistency:** All repositories now follow the same update schedule and grouping logic.
- **Reduced Noise:** Grouping related updates significantly reduces the number of open PRs.
- **Security:** Automated security updates are now active across the entire project ecosystem.
- **Clean Workspace:** Removed Renovate-specific boilerplate and configuration drift.

### Negative / costs

- Loss of some granular configuration features unique to Renovate (e.g., more complex auto-merge rules).
- One-time effort to migrate and standardize configuration files.

### Neutral

- Dependabot PRs still require manual or automated verification through existing CI workflows.

## Alternatives considered

1. **Standardize on Renovate:** Rejected because Renovate requires more complex configuration and often external hosting/tokens, whereas Dependabot is native to the platform.
2. **Maintain mixed tools:** Rejected because it perpetuates architectural drift and maintenance overhead.
3. **No automated updates:** Rejected as it creates a significant security and maintenance backlog.

## References

- `AGENTS.md`
- `z-shell-dot-github/decisions/0001-meta-repo-and-agents-md.md`
- `plan/z-shell-llm-management-plan.md`
