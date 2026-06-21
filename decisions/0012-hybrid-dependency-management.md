# 12. Split Dependency Updates Between Renovate and Dependabot

- **Status:** PROPOSED
- **Date:** 2026-06-21
- **Deciders:** None until accepted
- **Supersedes:** `decisions/0004-dependabot-unification.md`
- **Superseded by:** None

## Context

ADR 0004 standardized dependency management on Dependabot to remove a mixed,
inconsistent setup. The decision simplified administration, but routine version
updates still require a separate `.github/dependabot.yml` in every repository.
Those files have drifted across the organization in enabled ecosystems,
schedules, grouping, and target branches.

Z-Shell has more than 90 repositories spanning GitHub Actions, npm, Docker, Go,
Zsh plugins, documentation, and dependency references embedded in files that
native package managers do not always cover. The organization needs both:

- GitHub-native vulnerability detection and remediation; and
- centrally governed, flexible routine version maintenance.

Running Renovate and Dependabot for the same routine updates would recreate the
original fragmentation and add duplicate pull requests, lock-file conflicts,
and unnecessary CI usage.

## Decision

Adopt a hybrid model with non-overlapping ownership:

1. **GitHub Dependabot owns security:**
   - dependency graph;
   - Dependabot alerts;
   - Dependabot security update pull requests.
2. **Renovate owns routine version updates:**
   - GitHub Actions;
   - package-manager dependencies and lock files;
   - Docker images;
   - Go modules;
   - explicitly configured custom dependency references.
3. **No overlapping routine updates:** a repository covered by Renovate must
   not retain a `.github/dependabot.yml` that creates routine version-update
   pull requests.
4. **Central preset:** routine update policy lives in
   `z-shell/.github/renovate-config.json`. Repositories use automatic
   organization preset discovery or explicitly extend
   `local>z-shell/.github:renovate-config`.
5. **Conservative defaults:** the shared preset uses weekly scheduling, a
   minimum release age, grouped updates, semantic commits, and no global
   automerge.
6. **Repository exceptions stay local:** target branches, custom managers, or
   specialized grouping belong in a small repository `renovate.json`.

## Rollout and rollback

Migration is staged per repository:

1. Confirm the Renovate GitHub App can access the repository.
2. Confirm Renovate reads the shared preset and processes the repository.
3. Confirm the dependency graph, Dependabot alerts, and security updates remain
   enabled in GitHub settings.
4. Remove `.github/dependabot.yml` to stop overlapping routine updates.

If Renovate coverage is unavailable or fails, restore the repository's
Dependabot version-update configuration until coverage is healthy. A duplicate
routine update from both bots is a policy defect and must be resolved by
disabling the Dependabot version-update entry.

## Consequences

### Positive

- One organization preset controls routine update policy.
- GitHub remains the native authority for vulnerability alerts and fixes.
- Renovate supplies broader manager coverage, custom managers, release-age
  controls, grouping, and a Dependency Dashboard.
- Explicit ownership prevents duplicate update pull requests.
- Repository-specific configuration is limited to real exceptions.

### Negative / costs

- The Renovate GitHub App becomes an additional organization integration.
- App coverage and shared-preset validation must be monitored.
- Migration requires checking each repository before removing Dependabot
  version updates.
- Maintainers must understand that deleting `dependabot.yml` does not disable
  alerts or security updates configured in GitHub settings.

### Neutral

- Dependency pull requests still rely on repository CI and review policy.
- Security settings remain organization or repository settings rather than
  files inherited from the `.github` repository.

## Alternatives considered

1. **Dependabot only:** Rejected because configuration remains duplicated and
   has already drifted, while coverage and customization are narrower.
2. **Renovate only:** Rejected because GitHub already provides native
   vulnerability alerts and security remediation without granting an external
   app responsibility for the entire security path.
3. **Both tools for routine updates:** Rejected because it produces duplicate
   pull requests, conflicting lock-file changes, excess CI usage, and ambiguous
   ownership.

## References

- `decisions/0004-dependabot-unification.md`
- `runbooks/dependency-management.md`
- `renovate-config.json`
- [Renovate configuration presets](https://docs.renovatebot.com/config-presets/)
- [GitHub Dependabot security updates](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-security-updates)
