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

The organization-wide reconciler tracks actionable open issues in public
organization repositories. Private work remains in access-controlled records;
it must not be ingested or exported by this public automation. It excludes Renovate
Dependency Dashboard issues, which remain available in their owning
repositories as automation control surfaces. Project views separate workstreams:

- `Human delivery`: ordinary bugs, features, maintenance, and documentation
- `Automation`: recurring automation records requiring maintainer action
- `Dependency maintenance`: actionable routine dependency work
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
`PROJECT_TOKEN` to add every missing actionable open public organization issue to
Project 28. It also removes only exact Renovate Dependency Dashboard matches,
identified by bot type, bot login, and title. It is otherwise additive and
idempotent, emits a counts-only drift summary, and never overwrites human-set field values.
Manual dispatch remains read-only unless a maintainer sets `apply=true` after
reviewing the report.

`scripts/project_reconcile_live.py` collects API responses in memory, verifies
source repository visibility and organization ownership, and rechecks each
mutation target before applying it. Private and foreign-owner sources are
omitted. Redacted and draft Project items are counted but never mutated.
Unknown repository visibility, incomplete pagination, or transport errors fail
closed. GraphQL search inventories above 1,000 issues fail rather than silently
truncate; move to per-repository enumeration before exceeding that limit.

Only `project-reconcile-summary.json` is uploaded. Its schema is
`z-shell/project-reconcile-summary/v1`: fixed status text and aggregate counts,
with no source IDs, titles, URLs, labels, authors, raw API inputs, or diagnostic
payloads. Failures produce a sanitized error summary and a nonzero exit status.
The standalone NDJSON report CLI also exports only this summary. Detailed
records remain in memory for reconciliation; use authorized GitHub inspection
for per-item follow-up, never public workflow logs or artifacts. Counts are a
pre-apply snapshot; successful apply additionally reports verified mutation
counts. Failure may follow partial application, so inspect live membership
before retrying.

The credential-free `project-reconcile-test.yml` workflow runs synthetic
privacy and membership regressions on pull requests and changes to `main`.
Local verification uses:

```sh
python3 -m unittest discover -s scripts -p 'test_project_reconcile*.py' -v
python3 scripts/project_reconcile_live.py --output /tmp/project-reconcile-summary.json
```

The live command above is read-only. `--apply` requires separate maintainer
approval; CI uses `--require-token` to refuse fallback credentials when its
project-scoped token is unavailable.

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

The reconciliation summary counts stale open public issues: issues without an
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
changing reconciliation behavior. The summary reports counts for:

- open organization issues missing from Project 28
- omitted private, foreign-owner, draft, or unavailable Project records
- excluded Renovate Dependency Dashboard records and any matching Project items
- open issues that have been stale for five days, excluding `status:blocked`

Unclassified workstreams and conflicting or missing relationships require
separate authorized Project inspection; the scheduled summary does not assess
them. Do not treat a complete membership count as full portfolio readiness.

Any project membership, field, label, issue, repository, organization setting,
or workflow-setting mutation outside the scheduled additive reconciliation still
requires explicit maintainer approval.

## See also

- `AGENTS.md`
- `runbooks/triage.md`
- `runbooks/labels.md`
- `runbooks/sub-issues.md`
- `decisions/`
