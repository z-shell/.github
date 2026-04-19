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

The `.github` repository is a [special GitHub repository](https://docs.github.com/en/communities/setting-up-your-project-for-healthy-contributions/creating-a-default-community-health-file) that serves as the **organization-wide configuration hub**. Files placed here apply as defaults across all repositories in the [Z-Shell](https://github.com/z-shell) organization, without needing to duplicate them into every individual repository.

### What Makes It Special

| Feature | How It Works |
| --- | --- |
| **Organization Profile** | `profile/README.md` is rendered on the [organization's GitHub page](https://github.com/z-shell) as the public-facing profile. |
| **Default Community Health Files** | Files like `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `GOVERNANCE.md` in `.github/` are used as fallbacks by any org repository that doesn't define its own. |
| **Default Issue & PR Templates** | Templates in `.github/ISSUE_TEMPLATE/` and discussion forms in `.github/DISCUSSION_TEMPLATE/` are inherited by repositories without their own templates. |
| **Reusable Composite Actions** | The `actions/` directory hosts [composite actions](https://docs.github.com/en/actions/creating-actions/creating-a-composite-action) that any org repository can reference via `uses: z-shell/.github/actions/<name>@main`. |
| **Workflow Templates** | The `workflow-templates/` directory provides [starter workflows](https://docs.github.com/en/actions/using-workflows/creating-starter-workflows-for-your-organization) available in every org repository under **Actions > New workflow**. |
| **Shared Dependency Config** | `renovate-config.json` defines a shared [Renovate](https://docs.renovatebot.com/) preset that org repositories can extend for consistent automated dependency updates. |

> **Note:** The `.github` repository must be **public** for default community health files to apply across the organization.

---

## Repository Structure

| Path | Purpose |
| --- | --- |
| [`profile/`](../profile/) | Organization profile — the README and visual assets displayed on the [org page](https://github.com/z-shell) |
| [`actions/`](../actions/) | Reusable composite GitHub Actions shared across all org repositories |
| [`workflow-templates/`](../workflow-templates/) | Starter workflow templates available in the **Actions > New workflow** tab |
| [`metrics/`](../metrics/) | Auto-generated organization metrics and analytics |
| [`renovate-config.json`](../renovate-config.json) | Shared Renovate bot preset for dependency updates |

### Community Health Files

These files in `.github/` act as **organization-wide defaults** — automatically used by any repository that doesn't have its own version:

| File | Purpose |
| --- | --- |
| [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) | Contributor Covenant code of conduct |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Contribution guidelines and requirements |
| [`SECURITY.md`](SECURITY.md) | Security vulnerability reporting policy |
| [`GOVERNANCE.md`](GOVERNANCE.md) | Project governance roles and decision-making |
| [`CHARTER.md`](CHARTER.md) | Organizational charter and mission |
| [`STEERING_COMMITTEE.md`](STEERING_COMMITTEE.md) | Steering committee membership |
| [`MAINTAINERS.md`](MAINTAINERS.md) | Project maintainer list |
| [`TRADEMARKS.md`](TRADEMARKS.md) | Trademark usage policy |
| [`ANTITRUST.md`](ANTITRUST.md) | Antitrust compliance policy |
| [`ISSUE_TEMPLATE/`](ISSUE_TEMPLATE/) | Default issue forms (bug reports, features, docs, membership) |
| [`DISCUSSION_TEMPLATE/`](DISCUSSION_TEMPLATE/) | Default discussion category forms |

---

## Shared Actions

Composite actions available to all repositories via `z-shell/.github/actions/<name>`:

| Action | Description |
| --- | --- |
| [`setup-zsh`](../actions/setup-zsh) | Set up Zsh environment for CI |
| [`setup-zsh-development`](../actions/setup-zsh-development) | Set up Zsh development environment |
| [`build-zpmod-module`](../actions/build-zpmod-module) | Build the Zpmod Zsh module |
| [`test-zpmod-module`](../actions/test-zpmod-module) | Test the Zpmod module |
| [`test-zsh-module`](../actions/test-zsh-module) | Test Zsh modules |
| [`commit`](../actions/commit) | Automated commit action |
| [`rebase`](../actions/rebase) | Automated rebase action |
| [`mirror`](../actions/mirror) | Repository mirroring |
| [`rclone`](../actions/rclone) | File sync with rclone |
| [`determine-branch`](../actions/determine-branch) | Determine target branch |
| [`verify-pr-labels`](../actions/verify-pr-labels) | Verify PR label compliance |

**Usage example:**

```yaml
steps:
  - uses: z-shell/.github/actions/setup-zsh@main
```

## Workflow Templates

Starter workflows available in every org repository under **Actions > New workflow**:

| Template | Description |
| --- | --- |
| Commit Action | Automated commit workflow |
| Rebase Action | PR auto-rebase workflow |
| Lock Action | Issue/PR auto-lock |
| Stale Action | Stale issue management |
| Trunk | Trunk.io linting integration |
| Sync Labels | Label synchronization |
| Verify PR Labels | PR label validation |
| Rclone Action | File sync with rclone |

## Renovate

Shared [Renovate](https://docs.renovatebot.com/) preset for automated dependency updates. Reference from any org repository:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

---

## Common Use Cases

This repository is the right place for any **organization-level** configuration:

- **Adding a new default issue/PR template** — add it to `.github/ISSUE_TEMPLATE/`
- **Creating a reusable CI action** — add a composite action under `actions/<name>/action.yml`
- **Providing a starter workflow** — add `.yml` + `.properties.json` to `workflow-templates/`
- **Updating the organization profile** — edit `profile/README.md` or add assets to `profile/img/`
- **Changing contribution or security policies** — edit the corresponding file in `.github/`
- **Updating shared Renovate config** — edit `renovate-config.json`

For repository-specific overrides, add the same file to that repository directly — it will take precedence over the defaults from here.

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
