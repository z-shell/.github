# Runbook: Parent issues and sub-issues

Use this runbook to coordinate an outcome through GitHub's native parent issue,
sub-issue, and dependency relationships. GitHub Issues remain the work records;
Project 28 displays their delivery hierarchy and progress.

## When to use a parent issue

Create a parent issue only when one outcome requires at least two issues that
can be delivered, reviewed, or descoped independently. Use an issue checklist
for small actions that do not need their own ownership, discussion, or delivery
record.

Do not use a parent merely as a topic, label substitute, release bucket, or
duplicate roadmap. The normal hierarchy is one parent with direct sub-issues.
Add another level only when a separately owned outcome genuinely needs it.

## Ownership and labels

- Keep a parent whose required deliverables span repositories in
  `z-shell/.github`. Use the delivery initiative issue form there.
- Keep a parent and its sub-issues in the owning repository when the outcome is
  repository-local.
- Keep each implementation sub-issue in the repository that owns its change.
- Apply `meta:initiative` to the parent only. Never apply it to a sub-issue.
- Apply the normal work-type and area labels during triage. A cross-repository
  parent also qualifies for `meta:org-tracked` under the tracker policy.

The parent owns the coordinated outcome and its acceptance criteria. Each
sub-issue owns one independently deliverable result, its implementation detail,
and its pull request.

## Native relationships

Use GitHub's native sub-issue relationship between the parent and every
required deliverable. Do not maintain a duplicate task-list hierarchy in the
parent body.

Use native issue dependencies only for execution order or blockers. A
parent/sub-issue relationship expresses ownership, not ordering. When one
sub-issue blocks another, record the dependency between those issues and apply
the blocked workflow from `runbooks/triage.md` where appropriate.

Link each implementation pull request to its own sub-issue with a closing
keyword. A pull request should close the parent directly only when that single
pull request completes the entire coordinated outcome.

## Project 28 status

Add the parent and all required sub-issues to Project 28. Set each item's own
`Item Type`, `Impact`, `Effort`, and `Priority`; set `Target date` only for a
real commitment.

Use the parent status for the coordinated outcome:

- `Triage`: the outcome, owner, or required deliverable set is not agreed.
- `Todo`: the outcome is ready, but no required deliverable is active.
- `In Progress`: at least one required deliverable is active.
- `In Review`: required delivery is complete and the outcome awaits final
  confirmation.
- `Blocked`: a dependency prevents progress on the coordinated outcome. Also
  apply `status:blocked` to the parent.
- `Done`: the parent is closed under the closing rules below.

A blocked sub-issue does not automatically block the parent if other required
delivery can still progress. Keep child status on the child, and use Project
28's `Parent issue` and `Sub-issues progress` fields for roll-up rather than
copying progress counts into prose.

## Scope changes and closing

Close the parent only when every required deliverable is complete or explicitly
descoped. Record a descoping decision and its reason on the parent and affected
sub-issue. Keep the native relationship so the outcome's history remains
inspectable.

If a newly discovered deliverable is required for the outcome, add or create
its issue as a sub-issue before closing the parent. Reopen the parent if a
required deliverable reopens and the coordinated outcome is no longer complete.

## Review checklist

Before moving a parent out of triage, confirm that:

- the issue states one outcome and its acceptance criteria;
- it has at least two independently deliverable sub-issues;
- cross-repository ownership follows the rules above;
- `meta:initiative` appears only on the parent;
- native dependencies, rather than hierarchy, represent blockers or order;
- the parent and required sub-issues are visible in Project 28; and
- each issue has its own next action, owner or blocker, and triage fields.

Do not restructure the existing backlog merely to populate hierarchy views.
Pilot the workflow on the next real coordinated outcome, then expand it only
when the relationships improve ownership and progress visibility.

## See also

- [GitHub: Adding sub-issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/adding-sub-issues)
- [GitHub: Parent issue and sub-issue progress fields](https://docs.github.com/en/issues/planning-and-tracking-with-projects/understanding-fields/about-parent-issue-and-sub-issue-progress-fields)
- `AGENTS.md`
- `runbooks/labels.md`
- `runbooks/project-tracker.md`
- `runbooks/triage.md`
