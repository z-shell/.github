<div align="center">
  <a href="https://github.com/z-shell">
    <img src="https://raw.githubusercontent.com/z-shell/.github/main/profile/img/logo.svg" width="64" height="64" alt="Z-Shell" />
  </a>
  <h2>Z-Shell — Organization Configuration</h2>
  <p>
    Shared GitHub Actions, workflow templates, organization profile, and community assets.
  </p>
  <p>
    <a href="https://github.com/z-shell/.github/blob/main/LICENSE">
      <img src="https://img.shields.io/badge/License-MIT-23c88a?style=flat-square" alt="License" />
    </a>
  </p>
</div>

---

## About the `.github` Repository

The `.github` repository is a [special GitHub repository](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) and the **organization-wide configuration hub**. GitHub inherits supported community health files and templates from here; reusable actions, workflow templates, Renovate policy, ADRs, and runbooks remain shared resources that repositories or maintainers reference explicitly.

### What Makes It Special

| Feature                            | How It Works                                                                                                                                                                                                                              |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Organization Profile**           | `profile/README.md` is rendered on the [organization's GitHub page](https://github.com/z-shell) as the public-facing profile.                                                                                                             |
| **Default Community Health Files** | Files like `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `GOVERNANCE.md` in `.github/` are used as fallbacks by any org repository that doesn't define its own.                                                             |
| **Default Issue & PR Templates**   | Templates in `.github/ISSUE_TEMPLATE/` and discussion forms in `.github/DISCUSSION_TEMPLATE/` are inherited by repositories without their own templates.                                                                                  |
| **Agent Memory Protocol**          | `.github/AGENT_MEMORY.md` defines the GitHub-native handoff workflow used to keep cross-LLM and cross-repository progress visible.                                                                                                        |
| **Reusable Composite Actions**     | The `actions/` directory hosts [composite actions](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action) that any org repository can reference via `uses: z-shell/.github/actions/<name>@main`.                |
| **Workflow Templates**             | The `workflow-templates/` directory provides [starter workflows](https://docs.github.com/en/actions/using-workflows/creating-starter-workflows-for-your-organization) available in every org repository under **Actions > New workflow**. |
| **Shared Dependency Config**       | `renovate-config.json` defines the shared [Renovate](https://docs.renovatebot.com/) preset for routine version updates; GitHub Dependabot retains alerts and security updates.                                                            |

> **Note:** The `.github` repository must be **public** for default community health files to apply across the organization.

---

## Repository Structure

| Path                                              | Purpose                                                                                                     |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [`AGENTS.md`](../AGENTS.md)                       | Canonical org-wide instructions for AI coding agents and maintainers                                        |
| [`PATTERNS.md`](../PATTERNS.md)                   | Cross-repo implementation idioms grounded in real repositories                                              |
| [`decisions/`](../decisions/)                     | Architectural decision records for non-obvious org-wide choices                                             |
| [`runbooks/`](../runbooks/)                       | Repeatable operational workflows such as org review, triage, ADR drafting, and release coordination         |
| [`profile/`](../profile/)                         | Organization profile — the README and visual assets displayed on the [org page](https://github.com/z-shell) |
| [`actions/`](../actions/)                         | Reusable composite GitHub Actions shared across all org repositories                                        |
| [`workflow-templates/`](../workflow-templates/)   | Starter workflow templates available in the **Actions > New workflow** tab                                  |
| [`renovate-config.json`](../renovate-config.json) | Shared Renovate preset for routine dependency version updates                                               |

### Community Health Files

These files in `.github/` act as **organization-wide defaults** — automatically used by any repository that doesn't have its own version:

| File                                                 | Purpose                                                       |
| ---------------------------------------------------- | ------------------------------------------------------------- |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)           | Contributor Covenant code of conduct                          |
| [`CONTRIBUTING.md`](CONTRIBUTING.md)                 | Contribution guidelines and requirements                      |
| [`SECURITY.md`](SECURITY.md)                         | Security vulnerability reporting policy                       |
| [`GOVERNANCE.md`](GOVERNANCE.md)                     | Project governance roles and decision-making                  |
| [`CHARTER.md`](CHARTER.md)                           | Organizational charter and mission                            |
| [`STEERING_COMMITTEE.md`](STEERING_COMMITTEE.md)     | Steering committee membership                                 |
| [`MAINTAINERS.md`](MAINTAINERS.md)                   | Project maintainer list                                       |
| [`AGENT_MEMORY.md`](AGENT_MEMORY.md)                 | Cross-agent handoff and progress-tracking protocol            |
| [`copilot-instructions.md`](copilot-instructions.md) | Copilot entry point that defers to the canonical `AGENTS.md`  |
| [`TRADEMARKS.md`](TRADEMARKS.md)                     | Trademark usage policy                                        |
| [`ANTITRUST.md`](ANTITRUST.md)                       | Antitrust compliance policy                                   |
| [`ISSUE_TEMPLATE/`](ISSUE_TEMPLATE/)                 | Default issue forms (bug reports, features, docs, membership) |
| [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/)       | Default discussion category forms                             |

---

## Shared Actions

Composite actions currently available to all repositories via `z-shell/.github/actions/<name>`:

| Action                              | Description                 |
| ----------------------------------- | --------------------------- |
| [`setup-zsh`](../actions/setup-zsh) | Set up Zsh for CI workflows |
| [`commit`](../actions/commit)       | Commit generated changes    |
| [`rclone`](../actions/rclone)       | Sync files with rclone      |

**Usage example:**

```yaml
steps:
  - uses: z-shell/.github/actions/setup-zsh@main
```

## Workflow Templates

Starter workflows available in every org repository under **Actions > New workflow**:

| Template      | Description                 |
| ------------- | --------------------------- |
| Trunk         | Trunk code-quality workflow |
| Zsh CI        | Starter Zsh CI workflow     |
| Rclone Action | File sync with rclone       |

Label definitions live in [`./lib/labels.yml`](lib/labels.yml) and should be applied through org maintenance scripts or API-driven automation, not via a generic starter workflow template.

Task tracking is documented in [`../runbooks/project-tracker.md`](../runbooks/project-tracker.md).

## Dependency Management

Z-Shell separates routine maintenance from security remediation:

- [Renovate](https://docs.renovatebot.com/) owns routine dependency version updates.
- GitHub Dependabot owns dependency graph alerts and security update pull requests.

Repositories must not configure both bots for routine version updates. Renovate
discovers the shared organization preset automatically during onboarding, or a
repository can reference it explicitly:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

See [`../runbooks/dependency-management.md`](../runbooks/dependency-management.md)
for onboarding, validation, migration, and rollback.

---

## Common Use Cases

This repository is the right place for any **organization-level** configuration:

- **Adding a new default issue/PR template** — add it to `.github/ISSUE_TEMPLATE/`
- **Updating agent instructions, ADRs, runbooks, or patterns** — edit `AGENTS.md`, `decisions/`, `runbooks/`, or `PATTERNS.md`
- **Defining weekly review, ADR, or release coordination workflows** — add or update the relevant file under `runbooks/`
- **Recording cross-agent progress** — follow `.github/AGENT_MEMORY.md` and keep active state in issues, pull requests, and Linear
- **Managing organization task tracking** — follow `../runbooks/project-tracker.md`
- **Updating the shared label set** — edit `.github/lib/labels.yml` and roll it out via the org's maintenance automation
- **Cleaning legacy labels** — follow `../runbooks/labels.md` before deleting labels from live repositories
- **Creating a reusable CI action** — add a composite action under `actions/<name>/action.yml`
- **Providing a starter workflow** — add `.yml` + `.properties.json` to `workflow-templates/`
- **Updating the organization profile** — edit `profile/README.md` or add assets to `profile/img/`
- **Changing contribution or security policies** — edit the corresponding file in `.github/`
- **Updating dependency automation** — edit `renovate-config.json` and follow `../runbooks/dependency-management.md`

For a repository-specific Renovate exception, add a minimal `renovate.json` that
extends the organization preset and contains only the required override.

## Links

- [**Z-Shell Organization**](https://github.com/z-shell) — All repositories
- [**Wiki & Documentation**](https://github.com/z-shell/wiki) — Guides and reference
- [**Discussions**](https://github.com/orgs/z-shell/discussions) — Community forum
- [**GitHub Docs: Default Community Health Files**](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file)
- [**GitHub Docs: Workflow Templates**](https://docs.github.com/en/actions/using-workflows/creating-starter-workflows-for-your-organization)

---

<div align="center">
  <sub>Part of the <a href="https://github.com/z-shell">Z-Shell</a> organization</sub>
</div>
