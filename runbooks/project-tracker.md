# Runbook - Project tracker

Use this runbook for organization-wide work tracking in GitHub Project 28,
`z-shell Delivery`.

## Tracker identity

- Organization: `z-shell`
- Project: `https://github.com/orgs/z-shell/projects/28`
- Project number: `28`

GitHub Issues and pull requests remain the authoritative work records. Project
28 is the synchronized execution and portfolio view. Linear may mirror only
cross-repository, strategic, release-blocking, security-sensitive, or
organization-infrastructure work; it is not the source of truth.

## Inclusion policy

The organization-wide reconciler tracks all open organization issues so that
work cannot disappear between repositories. Project views separate workstreams:

- `Human delivery`: ordinary bugs, features, maintenance, and documentation
- `Automation`: bot dashboards and recurring automation records
- `Dependency maintenance`: routine dependency updates and dashboards
- `Security`: security work requiring maintainer attention
- `Administrative`: organization and repository governance

Pull requests are tracked when they are linked to a tracked issue, ready for
review, or otherwise explicitly added by a maintainer. Closed and merged items
move to `Done` and are archived after the review window.

Do not create standalone project-only work for a deliverable that belongs in a
repository issue. Use a draft issue only for temporary capture, then convert or
discard it during triage.

## Project fields and relationships

At triage, set `Item Type`, `Impact`, `Effort`, and `Priority`. Set `Target date`
only for a real commitment. Use native parent issues and sub-issues for
coordinated outcomes, and native issue dependencies for blockers.

Keep cross-repository parent issues in `z-shell/.github` and implementation
issues in their owning repositories. Link implementation pull requests with a
closing keyword.

## Automation model

The built-in auto-add workflow is intentionally not the long-term reconciler:
its filter language cannot exclude bot authors and the GitHub Free plan allows
only one auto-add workflow. Keep it narrow while the central reconciler is
introduced.

The staged reconciler is read-only by default. It uses a project-scoped
credential supplied as `PROJECT_TOKEN` and accepts an explicit `apply=true`
manual dispatch only after review. It must be idempotent, emit a drift report,
and never overwrite human-set field values without a documented rule.

The target implementation is an organization-owned GitHub App with Project
read/write permission, installed on all repositories, receiving only the
required issue, pull-request, repository, and installation events. A scheduled
reconciliation remains as recovery for missed webhook deliveries.

## Verification

Run the dry-run workflow manually and inspect its artifact before enabling any
write mode. The report must identify:

- open organization issues missing from Project 28
- project items whose source issue or pull request is no longer visible
- unclassified workstream records
- bot and dependency-dashboard records
- project items with conflicting or missing relationship data

Any project membership, field, label, issue, repository, organization setting,
or workflow-setting mutation still requires explicit maintainer approval.

## See also

- `AGENTS.md`
- `runbooks/triage.md`
- `runbooks/labels.md`
- `decisions/`
