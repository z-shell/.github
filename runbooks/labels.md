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
2. Run a dry-run audit before applying anything:

   ```sh
   scripts/labels-sync.rb --repo z-shell/REPO
   ```

   For an org-wide read-only report:

   ```sh
   scripts/labels-sync.rb --all-repos > /tmp/z-shell-labels-dry-run.md
   ```

3. Create or update every canonical label from `.github/lib/labels.yml`.
4. For each legacy label, find open issues and pull requests using it.
5. Add the canonical replacement to each item before removing the legacy label.
6. Delete legacy labels only after they are no longer used.
7. Re-run the dry-run audit and compare it with `.github/lib/labels.yml`.

Do not delete unknown labels in bulk. If a repository has a local label that is not obviously legacy, open or update an issue before removing it.

## Label sync script

`labels-sync.rb` is the canonical entrypoint. The older `scripts/labels-dry-run.rb` name remains as a compatibility wrapper for existing local commands, but new runbook examples should use `scripts/labels-sync.rb`.

`scripts/labels-sync.rb` is read-only by default. It consumes `lib/labels.yml`, queries GitHub through `gh api`, and reports:

- canonical labels that would be created
- canonical labels whose color or description would be updated
- legacy labels that should be migrated before removal
- unknown local labels that should be preserved and reviewed manually

Useful examples:

```sh
# Audit one repository and include clean output.
scripts/labels-sync.rb --repo z-shell/.github --include-clean

# Audit several repositories.
scripts/labels-sync.rb --repo z-shell/zi --repo z-shell/wiki

# Emit machine-readable output for follow-up tooling.
scripts/labels-sync.rb --repo z-shell/zi --json
```

## Apply-mode pilot

Apply mode is intentionally limited while #411 is piloted:

- default mode remains read-only;
- `--apply` previews canonical label create/update operations without mutating anything;
- `--apply --confirm-apply` may only create missing canonical labels and update canonical label metadata;
- it does not delete unknown labels;
- it does not delete legacy labels;
- it does not migrate labels on issues or pull requests;
- org-wide apply is disabled during the pilot;
- confirmed apply requires explicit `--repo` values;
- confirmed apply is limited to the temporary pilot allowlist unless a maintainer explicitly approves `--allow-non-pilot-repo`.

Preview commands:

```sh
# Preview canonical create/update operations for one repo.
scripts/labels-sync.rb --repo z-shell/REPO --apply

# Preview in JSON for artifact comparison.
scripts/labels-sync.rb --repo z-shell/REPO --apply --json
```

Confirmed apply commands require maintainer approval because they mutate GitHub labels:

```sh
# No-op safety apply on the clean org metadata repo.
scripts/labels-sync.rb --repo z-shell/.github --apply --confirm-apply --include-clean

# Approved pilot outside the temporary allowlist.
scripts/labels-sync.rb \
  --repo z-shell/REPO \
  --apply \
  --confirm-apply \
  --allow-non-pilot-repo
```

## See also

- `.github/lib/labels.yml`
- `runbooks/triage.md`
- `runbooks/org-review.md`
