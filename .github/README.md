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

## 📁 Repository Structure

| Directory | Purpose |
|:--|:--|
| [`profile/`](../profile/) | Organization profile — README and visual assets displayed on the [org page](https://github.com/z-shell) |
| [`actions/`](../actions/) | Reusable composite GitHub Actions shared across organization repositories |
| [`workflow-templates/`](../workflow-templates/) | Starter workflow templates available in the **Actions → New workflow** tab |
| [`metrics/`](../metrics/) | Auto-generated organization metrics and analytics |

## ⚡ Shared Actions

Composite actions available to all repositories via `z-shell/.github/actions/<name>`:

| Action | Description |
|:--|:--|
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

## 📋 Workflow Templates

Starter workflows available in the organization's **Actions** tab:

| Template | Description |
|:--|:--|
| Commit Action | Automated commit workflow |
| Rebase Action | PR auto-rebase workflow |
| Lock Action | Issue/PR auto-lock |
| Stale Action | Stale issue management |
| Trunk | Trunk.io linting integration |
| Sync Labels | Label synchronization |
| Verify PR Labels | PR label validation |
| Rclone Action | File sync with rclone |

## 🔧 Renovate

Shared [Renovate](https://docs.renovatebot.com/) preset for automated dependency updates. Reference from any org repository:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

## 🔗 Links

- [**Z-Shell Organization**](https://github.com/z-shell) — All repositories
- [**Wiki & Documentation**](https://github.com/z-shell/wiki) — Guides and reference
- [**Discussions**](https://github.com/orgs/z-shell/discussions) — Community forum

---

<div align="center">
  <sub>Part of the <a href="https://github.com/z-shell">Z-Shell</a> organization</sub>
</div>
