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
closing keyword. Apply `meta:initiative` only to qualifying parent issues and
follow `runbooks/sub-issues.md` for ownership, status, and closing rules.

## Automation model

The built-in auto-add workflow is intentionally not the long-term reconciler:
its filter language cannot exclude bot authors and the GitHub Free plan allows
only one auto-add workflow. Keep it narrow while the central reconciler is
introduced.

The scheduled reconciler uses a project-scoped credential supplied as
`PROJECT_TOKEN` to add every missing open organization issue to Project 28. It
is additive and idempotent, emits a drift report, and never overwrites
human-set field values. Manual dispatch remains read-only unless a maintainer
sets `apply=true` after reviewing the report.

The target implementation is an organization-owned GitHub App with Project
read/write permission, installed on all repositories, receiving only the
required issue, pull-request, repository, and installation events. A scheduled
reconciliation remains as recovery for missed webhook deliveries.

## Managed progress

Project membership prevents work from disappearing. It does not prove that work
is managed. Every substantive task must have an owning issue, visible Project
28 triage state, and material progress recorded on its issue or pull request.
Record a next action or blocker when work starts, becomes blocked, is ready for
review, or is handed off. Assignment alone is not active management.

The reconciliation artifact lists `stale_open_issues`: open issues without an
update for five days. Items labeled `status:blocked` are excluded so that the
blocked workflow remains explicit. This is a review queue only. It must never
automatically comment, label, close, or otherwise mutate an issue.

At least weekly, review missing, stale, blocked, and untriaged work. Resolve
each candidate by recording a next action, blocker, deferral, or closure, then
publish a Project status update that states portfolio health and material risks.
Configure Project 28's built-in workflows to set new items to `Todo` and closed
issues or merged pull requests to `Done`. Archive completed items only after
the agreed retention period.

## Verification

Run the workflow manually without `apply=true` and inspect its artifact before
changing reconciliation behavior. The report must identify:

- open organization issues missing from Project 28
- project items whose source issue or pull request is no longer visible
- unclassified workstream records
- bot and dependency-dashboard records
- project items with conflicting or missing relationship data
- open issues that have been stale for five days, excluding `status:blocked`

Any project membership, field, label, issue, repository, organization setting,
or workflow-setting mutation outside the scheduled additive reconciliation still
requires explicit maintainer approval.

## See also

- `AGENTS.md`
- `runbooks/triage.md`
- `runbooks/labels.md`
- `runbooks/sub-issues.md`
- `decisions/`
