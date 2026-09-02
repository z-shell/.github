# Runbook — Label maintenance

Use this runbook when cleaning or syncing labels across z-shell repositories.

## Sync scope

Canonical label sync targets **active, public, non-fork** repositories only.
`scripts/labels-sync.rb --all-repos` audits every repository the token can see,
so its raw output is wider than the sync scope. Filter before reading drift
totals, or private and fork repositories will keep reporting as regressions
when they are simply out of scope.

Excluded, and why:

- **Private repositories.** Not part of the public contributor-facing label
  surface. Currently `z-shell/.github-private` and `z-shell/.trunk`.
- **Forks.** Their label sets largely belong to the upstream project, and
  rewriting them loses that provenance without benefiting z-shell contributors.
- **Archived repositories.** Read-only by definition.

The exclusion is deliberate, not a backlog. Do not treat drift in these
repositories as a finding, and do not include them in org-wide totals without
saying which scope the number uses. If a repository leaves fork or private
status and becomes an active public repository, it enters scope at that point
and should be synced like any other.

## Source of truth

`lib/labels.yml` is the canonical organization label set.

Use compact namespace names:

- `type:bug`, not `type: bug`
- `area:docs`, not `area: docs`
- `priority:high`, not `priority: high`
- `status:triage`, not `status: triage`

The org tracker auto-add label is `meta:org-tracked`. The parent-only delivery
label is `meta:initiative`; follow `runbooks/sub-issues.md` before applying it.

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
- `performance`
- `breaking-change`
- `status:triage`
- `status:blocked`
- `needs-info`
- `good first issue`
- `help wanted`
- `invalid`
- `duplicate`
- `wontfix`

### Coordination metadata

- `meta:initiative`
- `meta:org-tracked`
- `meta:no-issue`

`meta:no-issue` is the traceability exemption defined by
`decisions/0022-issue-traceability-on-pull-requests.md`. Apply it only to a
pull request that genuinely has no owning work item, such as gitlink and
submodule reconciliation or a routine dependency update. ADR-0022 makes
applying it a maintainer decision: an agent may propose it and must not apply
it on its own authority. Every other pull request closes or references an
issue instead.

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
| `performance 🚀`           | `performance`       |
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

3. Create or update every canonical label from `lib/labels.yml`.
4. For each legacy label, find open issues and pull requests using it.
5. Add the canonical replacement to each item before removing the legacy label.
6. Delete legacy labels only after they are no longer used.
7. Re-run the dry-run audit and compare it with `lib/labels.yml`.

Do not delete unknown labels in bulk. If a repository has a local label that is not obviously legacy, open or update an issue before removing it.

`labels-sync.rb` enforces this: `sync_policy.delete_unknown_labels` is `false`
and the script never deletes an unknown label. Leave that setting alone. An
approved sweep is a one-off operation, not a reason to make deletion the
default.

### Exception: an approved unknown-label sweep

The prohibition above is the default and stays the default. A bulk deletion is
permitted only as a separately approved operation that meets every condition
below. Missing any one of them means the sweep does not proceed.

1. **Explicit maintainer approval**, given against figures measured at approval
   time rather than against an earlier report.
2. **Usage measured live from `repos/OWNER/REPO/issues?state=all`**, counting
   items in every state. Never use the issue search API: its index lags bulk
   label changes badly enough to report labels as in use months after they were
   removed, and it fails in both directions.
3. **Delete only definitions attached to zero items.** A label carrying even one
   item is migrated or left alone, never deleted.
4. **Preserve anything referenced by configuration**, verified by reading the
   files rather than assuming. At minimum check `.github/labeler.yml` and the
   `stale-*-label` and `exempt-*-labels` inputs of any stale or lock workflow.
   Deleting a referenced label does not fail loudly; `actions/labeler` recreates
   it on the next matching pull request, so the sweep quietly undoes itself.
5. **Archive every label definition** in the affected repositories, including
   color and description, before the first write, so any deletion is
   restorable.
6. **Pilot on one low-traffic repository** and verify it by hand before the
   remaining repositories.
7. **Batch per repository with per-operation logging**, so a failure is
   contained and attributable.
8. **Re-audit afterwards and re-derive the justification for every survivor**,
   rather than trusting the plan that was executed.

Record the result on the owning issue, including the counts before and after
and the exclusion list actually applied.

The 2026-08-19 sweep is the reference execution: 1,483 unknown definitions
across the 86 in-scope repositories reduced to 93, with 1,390 deleted and every
survivor re-verified as in use or configuration-referenced.

## Label sync script

`scripts/labels-sync.rb` is the canonical entrypoint. The older `scripts/labels-dry-run.rb` name remains as a compatibility wrapper for existing local commands, but new runbook examples should use `scripts/labels-sync.rb`.

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

- `lib/labels.yml`
- `runbooks/triage.md`
- `runbooks/org-review.md`
- `runbooks/sub-issues.md`
