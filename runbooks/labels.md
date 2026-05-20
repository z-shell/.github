# Runbook — Label maintenance

Use this runbook when cleaning or syncing labels across z-shell repositories.

## Source of truth

`.github/lib/labels.yml` is the canonical organization label set.

Use compact namespace names:

- `type:bug`, not `type: bug`
- `area:docs`, not `area: docs`
- `priority:high`, not `priority: high`
- `status:triage`, not `status: triage`

The org tracker auto-add label is `meta:org-tracked`.

## Canonical groups

### Work type

- `type:bug`
- `type:feature`
- `type:docs`
- `type:question`
- `type:maintenance`
- `type:membership`
- `type:handoff`

### Area

- `area:zi`
- `area:plugin`
- `area:annex`
- `area:package`
- `area:docs`
- `area:ci`
- `area:dependencies`
- `area:release`
- `area:meta`

### Severity and modifiers

- `priority:high`
- `regression`
- `security`
- `breaking-change`
- `status:triage`
- `status:blocked`
- `needs-info`
- `good first issue`
- `help wanted`
- `invalid`
- `duplicate`
- `wontfix`
- `meta:org-tracked`

## Retire old labels

Retire old labels only after preserving labels on open issues and pull requests.

Common legacy labels:

| Legacy label               | Canonical label     |
| -------------------------- | ------------------- |
| `bug 🐞`                   | `type:bug`          |
| `feature-request 💡`       | `type:feature`      |
| `new-feature 🎉`           | `type:feature`      |
| `documentation 📝`         | `type:docs`         |
| `Q&A ✍️`                   | `type:question`     |
| `enhancement ✨`           | `type:maintenance`  |
| `maintenance 📈`           | `type:maintenance`  |
| `agent-memory 🧠`          | `type:handoff`      |
| `👥 member`                | `type:membership`   |
| `annex 🌀`                 | `area:annex`        |
| `plugin ⚙️`                | `area:plugin`       |
| `package 📦`               | `area:package`      |
| `ci 🤖`                    | `area:ci`           |
| `github-actions :octocat:` | `area:ci`           |
| `dependencies 📦`          | `area:dependencies` |
| `javascript 📦`            | `area:dependencies` |
| `submodules ⚙️`            | `area:dependencies` |
| `high-priority 🔥`         | `priority:high`     |
| `triage 📑`                | `status:triage`     |
| `priority-low 🔖`          | `status:blocked`    |
| `beginner-friendly`        | `good first issue`  |
| `help-wanted`              | `help wanted`       |
| `breaking-change 💥`       | `breaking-change`   |
| `security 🛡️`              | `security`          |
| `invalid ⚠️`               | `invalid`           |

Also retire spaced namespace variants such as `type: bug`, `area: docs`, `priority: high`, and `status: triage`.

## Safe cleanup order

1. List labels in the target repository.
2. Create or update every canonical label from `.github/lib/labels.yml`.
3. For each legacy label, find open issues and pull requests using it.
4. Add the canonical replacement to each item before removing the legacy label.
5. Delete legacy labels only after they are no longer used.
6. Re-run the label list and compare it with `.github/lib/labels.yml`.

Do not delete unknown labels in bulk. If a repository has a local label that is not obviously legacy, open or update an issue before removing it.

## See also

- `.github/lib/labels.yml`
- `runbooks/triage.md`
- `runbooks/org-review.md`
