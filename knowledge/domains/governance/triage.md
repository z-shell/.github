# Runbook: Triage

Classify issues and pull requests, verify whether work is still needed, and maintain the owning GitHub record and Project 28 view. GitHub remains authoritative; Linear is a selective linked mirror.

## Authority and scope

Reading, investigation and drafting are read-only. Ask once for a bounded delivery scope that names the repository, owning issue and its implementation pull requests, and includes the routine metadata operations below. A maintainer may authorize that scope with implementation and PR publication. Record the approved operations and reuse that authority while the targets and scope remain unchanged; do not ask again for each covered label or progress update.

Routine metadata authority covers adding existing canonical work-type and area labels to those issues and pull requests, ensuring their eligible Project 28 membership, and updating their factual delivery status. It does not cover replacing existing classifications or clearing human-set fields. Before a status write, inspect relevant configured automation; if its downstream effects cannot be verified, draft that write rather than assuming it only changes a display field.

Approval to investigate, edit locally or publish a PR does not by itself grant this metadata scope. Include it explicitly in the delivery approval. Earlier narrow approvals remain narrow. Without authority, prepare the proposed changes and report the missing approval rather than omitting metadata from the handoff.

Seek a separate decision for disputed classification, priority or impact changes, effort commitments, assignees, deadlines, label removal, disposition labels (`invalid`, `duplicate`, `wontfix`), coordination labels (`meta:initiative`, `meta:org-tracked`), and the maintainer-only `meta:no-issue` exemption. Comments, issue creation or closure, merges, Linear writes, settings changes and label-definition maintenance retain their explicit authorization boundaries; they can be bundled when the exact operations are requested, but are not implied by routine metadata authority.

Unattended reviews, weekly sweeps, bulk backfills and stale/lock dispositions remain draft-only under [recurring operations](../../../runbooks/recurring-operations.md) unless their own scope is explicitly authorized. This runbook grants no new automation or credential permissions.

## When to triage

- Review new issues and PRs within the existing 48-hour target, sooner for active repositories such as `zi` and `wiki`.
- Include triage when starting an approved issue, opening its PR, recording a blocker, handing off for review and verifying completion.
- Review missed items weekly, and promptly escalate security, regression, release-blocking or cross-repository reports to the responsible maintainer.

If a quick queue pass cannot establish the facts, record the unknowns and next investigation under the owning item. Propose `status:triage` when appropriate rather than inventing a label or treating an unverified issue as ready for implementation. A quick pass does not replace the investigation gate below.

## Filing a new issue

An issue filed through the API, including `gh issue create --body-file`, bypasses the repository's issue forms: their required fields, labels and assignees never apply. When creating an issue is authorized, follow the form by hand:

1. Find the effective form. If the owning repository has a `.github/ISSUE_TEMPLATE/` directory, its forms apply; otherwise this repository's `.github/ISSUE_TEMPLATE/` forms apply. Any file in the repository directory, `config.yml` alone included, replaces every organization form. Pick the form that matches the work type.
2. Write one `### <label>` heading per `input`, `textarea` and `dropdown` field, in form order, using the field's `label` text exactly, as GitHub renders a submitted form. Fill every required field; write `Not applicable` and the reason rather than dropping a heading. Leave out `markdown` blocks and policy `checkboxes`.
3. In reproduction and environment fields, give the exact revision (branch and commit), the Zsh version, the OS, the shortest isolated reproduction (`zsh -f`, with an isolated `HOME` when configuration matters), and the actual and expected output.
4. Apply the form's `labels` and `assignees` together with the canonical `type:*` and `area:*` labels from step 3 below. Use the form's title prefix unless the owning repository's instructions set another title style.
5. Read the issue back and compare its headings and labels with the form before reporting it filed.

## 1. Inspect context and ownership

1. Resolve the exact repository, item, visibility, current state, acceptance criteria and intended target branch. Read the complete issue discussion and relevant PR feedback.
2. Inspect existing labels, assignees, issue type, Project 28 membership and field values, native dependencies, parent/sub-issues, linked PRs and prior handoffs. Keep existing human decisions unless their replacement is approved.
3. Search open and closed issues and PRs in the owning repository, relevant organization repositories, commit history, accepted ADRs and existing patterns. Prefer the existing owner to a duplicate issue.
4. Distinguish a confirmed defect from a design request, support question, completed work or unverified report. For a PR, classify its actual complete diff rather than inheriting the issue's labels blindly.

Handle vulnerability details through the [security policy](../../../.github/SECURITY.md) and [incident response runbook](../../../runbooks/security-incident-response.md) before public classification. Public hardening work can carry `security`; private exploit evidence must not be exposed by a public item, label, comment or mirror.

## 2. Investigate and recommend one disposition

An open issue is a hypothesis, not proof that implementation remains necessary or valuable.

1. Verify live project fields, dependencies and blockers, and record the current target-branch commit.
2. Trace the affected implementation and callers. Reproduce the behavior or state why reproduction is unavailable; run the smallest meaningful checks.
3. Assess organization conventions, shared workflows, affected repositories and compatibility implications before selecting an implementation.
4. Compare correctness, user, security, performance and maintenance value with cost, regression risk and continuing ownership. Do not claim a performance benefit without measurement.
5. Recommend exactly one disposition: implement, defer, close as completed, close as not planned, or request more information. Closure recommendations remain proposals until authorized.

Report the recommendation, current reality and history, the confirmed finding, value versus cost, validation and evidence gaps, and the next authorized action. Cite exact source locations, revisions and relevant issue or PR evidence. Preserve useful out-of-scope findings under an existing owner or propose a separate issue; do not widen implementation silently.

## 3. Classify with canonical labels

[knowledge/domains/governance/data/labels.yml](../../../knowledge/domains/governance/data/labels.yml) owns label names and definitions. Every triaged issue and PR needs a work-type label and, when known, at least one area label. Inspect current repository definitions before applying them. Missing definitions belong to the [label maintenance procedure](../../../runbooks/labels.md), not an opportunistic create or rename during triage.

| Work                             | Label              |
| -------------------------------- | ------------------ |
| Broken behavior                  | `type:bug`         |
| New capability                   | `type:feature`     |
| Documentation only               | `type:docs`        |
| Maintenance or organization work | `type:maintenance` |
| Support or clarification         | `type:question`    |
| Membership                       | `type:membership`  |
| A dedicated handoff issue        | `type:handoff`     |

Use the matching area from the canonical set: `area:zi`, `area:plugin`, `area:annex`, `area:package`, `area:docs`, `area:ci`, `area:dependencies`, `area:release`, or `area:meta`. Area describes the affected work, not just the repository name. A documentation PR for CI can carry `type:docs` and `area:ci`. A progress comment does not turn its owning implementation issue into `type:handoff`.

Preserve unrelated, repository-local and automation-owned labels. Add only evidence-supported classifications within the approved scope; propose conflicting replacements. Do not rewrite the complete label set to add one missing label.

Apply modifiers only for their actual meaning: a demonstrated regression, a supported performance concern, a confirmed breaking change, an initial triage need, or a documented blocker. `good first issue` and `help wanted` express contributor suitability and maintainer intent, not an automatic property of a small diff. Explain material judgments in the triage record; routine type/area additions need no separate comment merely to repeat their definitions.

Follow [sub-issues](../../../runbooks/sub-issues.md) for parent eligibility and `meta:initiative`. Follow [ADR-0022](../../../decisions/0022-issue-traceability-on-pull-requests.md) for `meta:no-issue`. Neither is ordinary classification authority. Do not infer a Linear mirror from `meta:org-tracked` alone.

## 4. Reconcile Project 28 and progress

Follow [project tracking](../../../runbooks/project-tracker.md) for inclusion, privacy, field discovery and reconciliation. Verify the owning issue's visible triage state before substantive implementation. Include its implementation PR under that runbook's inclusion policy; issue membership alone does not establish PR membership or managed progress.

Discover actual field and option IDs. Labels, native GitHub issue types and Project `Item Type` are distinct surfaces; do not assume one populates the others. At triage, propose `Item Type`, `Impact`, `Effort`, `Priority` and the applicable `Workstream`. Populate approved values without overwriting human decisions. Set `Target date` only for a real commitment and assign a person only with authority and a known owner.

### Priority

These are delivery priorities, not a substitute for security severity under ADR-0010. Retain the existing bands and use the live Project options, rather than inventing a label for every band.

| Band     | Meaning                                                                    | Project 28 option |
| -------- | -------------------------------------------------------------------------- | ----------------- |
| Critical | Data loss, security vulnerability, or complete breakage with no workaround | `P0 - Critical`   |
| High     | Significantly impacts users or blocks important work; schedule next        | `P1 - High`       |
| Medium   | Important but not urgent; prioritize against other planned work            | `P2 - Medium`     |
| Low      | Nice to have; no fixed timeline                                            | `P3 - Low`        |

`priority:high` covers the top two bands only. The existing conceptual `None` means no agreed priority; Project 28 currently has no `None` option. Record the unresolved decision without setting an invented value or clearing an existing priority. Re-discover options before writes; these names are not hard-coded API identifiers.

### Delivery status

- `Triage`: facts, scope, disposition or ownership still need agreement.
- `Todo`: work is agreed and ready, but execution has not started.
- `In Progress`: approved work is active.
- `In Review`: the tracked deliverable is ready and awaiting the required review or maintainer decision.
- `Blocked`: a recorded dependency prevents progress on that item's deliverable.
- `Done`: the owning deliverable is complete; verify closure or merge and the project transition.

A partial PR can be complete while its issue remains open with outstanding criteria. Set each item from its own scope, not the state of any linked PR. Parent progress follows [sub-issues](../../../runbooks/sub-issues.md), not a copied child status. Reconcile any other configured status, including `Won't Fix`, only after its disposition is explicitly decided.

### Blocked workflow

Record the dependency or decision, its owner, the next unblock action and any useful review condition. Use a native dependency for an actual issue blocker. Propose or, with explicit scope, apply `status:blocked` and Project `Blocked` together; do not suppress a stale item merely because it is old. When the blocker clears, verify that fact, remove the obsolete blocked marker with authority, and restore the appropriate delivery state. Do not invent an unblock date.

Blocked items are excluded from the reconciler's stale queue; inaccurate blocked labels can conceal unmanaged work. A blocked child does not automatically block a parent that still has actionable required delivery.

## 5. Record the next action and optional mirror

Keep the record concise and useful: evidence and disposition, owner or unresolved ownership, next action or blocker, verification and limitations, and the issue/PR links. Use [the handoff protocol](../../../.github/AGENT_MEMORY.md) for unfinished work and [the PR runbook](../../../runbooks/pull-requests.md) for review readiness. Update the existing body or post a comment only within its authorized scope. No acknowledgment-only comment is required when the existing record already gives the needed evidence and next action. Do not promise delivery dates.

GitHub remains authoritative. A linked Linear mirror is eligible for cross-repository, release-blocking, security-sensitive, strategic or organization-infrastructure work under [project tracking](../../../runbooks/project-tracker.md). Eligibility is not proof of a configured integration or authorization to write in Linear.

Search for an existing mirror and inspect the actual repository/team sync configuration before expecting ingestion. Linear supports configured one-way or two-way sync; historical issues require import, and GitHub Project custom statuses do not sync to Linear. Discover the team's fields, estimate scale and workflows instead of assuming fixed options. Keep private evidence out of public mirrors. Do not enable an integration or create broad sync during triage.

## 6. Verify writes and close only with evidence

Before any approved mutation, refresh the target and its existing metadata. Apply only the approved change; use file input for multiline bodies and comments, then read stored fields back. Check relevant downstream automation and verify the observable result. If automation or permissions prevent verification, report the exact gap without broadening credentials or assuming success.

A label added successfully does not prove triage is complete. Confirm the work-type and area labels, appropriate project membership and agreed fields, a current next action or blocker, and traceability to the owning issue. Explicitly name anything drafted, skipped or unavailable.

Close only when the maintainer has authorized the disposition. A completed disposition requires every owning acceptance criterion to be met or explicitly descoped; duplicate, invalid and not-planned dispositions require their own evidence and approved rationale. Record the reason and fixing PR/commit, canonical duplicate, or rationale for not proceeding. Partial work uses `Refs`, not premature `Closes`; merging its PR must not mark the whole issue complete. Verify Project 28's final state rather than assuming an automation ran. Approving or merging a PR remains a separate decision.

When evidence or repository history disproves a recommendation, follow [learning capture](../../../runbooks/learning-capture.md). Useful recurring gaps should improve the smallest canonical owner; do not add a duplicate policy, skill or workflow merely to demonstrate that the review happened.

## Special cases and anti-patterns

New-contributor PRs need specific, actionable guidance and a concrete next step. Avoid unnecessary reproduction requests for defects already established by repository evidence.

Do not silently leave metadata incomplete, repeatedly request already granted scope, replace human classifications, create duplicate owners, mass-close stale items, or leave blocked/triage work without an owner or next action. Security intake and bulk operations keep their separately scoped procedures.

## References

- [Organization instructions](../../../AGENTS.md)
- [Canonical labels](../../../knowledge/domains/governance/data/labels.yml) and [label maintenance](../../../runbooks/labels.md)
- [Project tracking](../../../runbooks/project-tracker.md) and [sub-issues](../../../runbooks/sub-issues.md)
- [PR lifecycle](../../../runbooks/pull-requests.md) and [learning capture](../../../runbooks/learning-capture.md)
- [Security policy](../../../.github/SECURITY.md) and [incident response](../../../runbooks/security-incident-response.md)
- [GitHub labels](https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/managing-labels)
- [GitHub Project automations](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-built-in-automations)
- [Linear GitHub integration](https://linear.app/docs/github)
