# Runbook: Recurring Operations

Use this runbook to classify and review scheduled workflows and other recurring
organization maintenance.

## Purpose and boundary

Recurring work should run only as often, and with only as much authority, as its
value requires. This runbook separates deterministic automation from
maintainer judgment and provides one evidence record for each classification.

**Hard rule:** except for the explicitly authorized
[Zsh Plugin Standard review issue](#review-the-zsh-plugin-standard-twice-yearly),
every review described here produces a draft only. Do not add labels, post
comments, close or lock issues or pull requests, dispatch workflows, change
settings, or modify repositories unless a maintainer approves that action as a
separate, scoped step.

This runbook does not create a Codex schedule or any other scheduler. Evaluate
the scheduler's supported capabilities and authority before proposing one.

The sources of truth are:

- the live workflow definition, state, and recent runs in the owning repository;
- repository activity and the owning GitHub issue or pull request;
- the relevant organization runbook, accepted decision record, and
  [recurring-operations coordination issue](https://github.com/z-shell/.github/issues/485).

An inventory or review draft is evidence, not a replacement for those owners.

## Choose scheduled, event-driven, reusable, or manual work

Apply this decision tree to each operation:

1. Does time change the operation's input or value?
   - If yes, consider a schedule.
   - If no, continue to the next question.
2. Does a source change, pull request, tag, label-definition change, or
   repository creation supply the real input?
   - If yes, use the narrow matching event-driven trigger.
   - If no, continue to the next question.
3. Is the execution deterministic and repeated across repositories?
   - If yes, centralize the tested execution in a reusable workflow. Each
     caller still owns its trigger, permissions, concurrency, and target-branch
     authority.
   - If no, continue to the next question.
4. Does the work require judgment, private evidence, mutation, or credentials
   broader than one narrow operation?
   - If yes, keep it manual and require explicit approval.
   - If no, document why automation provides observable value before adding it.

Use a schedule only when elapsed time creates a meaningful new input, such as a
certificate approaching expiry or a periodic external data snapshot. A
schedule is not a substitute for a missing event trigger.

## Record the classification

Create one record per workflow. Refresh live state before filling it in.

```text
Repository:
Workflow path:
Purpose:
Repository class:
Current workflow state:
Cron and timezone:
Event-driven triggers:
Owning runbook or issue:
Required permissions:
Concurrency behavior:
Latest scheduled result:
Repeated failure signature:
Observed value:
Classification: retain | event-driven | reusable | manual | remove
Decision evidence:
Follow-up owner:
Retirement condition:
```

Do not infer value from file presence or from one successful run. State what
the workflow detects, prevents, publishes, or maintains, and cite the evidence.

## Keep public and private evidence separate

A public report may contain public repository names, workflow paths, schedules,
documented permissions, aggregate results, and links to public issues or runs.

A private report is required when the target set or evidence includes private
repository identities, administrative settings, credentials, private run
output, security-sensitive findings, or unpublished operational details.
Before publishing any derivative:

1. remove private repository and workflow identities;
2. remove local paths, host details, tokens, credential names, and secret
   values;
3. replace sensitive samples with aggregate counts or a public-safe
   description;
4. verify every link and quoted field is already public;
5. save private artifacts with restricted access and keep them out of the
   repository.

If sanitization would remove the evidence needed to support a conclusion, keep
the entire conclusion private.

## Design least-privilege automation

Every workflow must declare explicit `permissions`. Start with no permissions
or read-only contents, then grant only the operations required by the specific
job. Prefer the repository-scoped `GITHUB_TOKEN`; use a narrowly scoped GitHub
App, OpenID Connect trust policy, or dedicated credential only when the
repository token cannot perform the required operation.

Pin actions and reusable workflows to a full commit SHA. Treat a mutable branch
or tag reference as unreviewed code unless a documented platform constraint
requires it. Pass only the secrets a called workflow needs, and ensure nested
workflow permissions can only stay the same or become more restrictive.

Never provision a broad unattended organization write token. Mutating
organization operations require a separately reviewed design, narrow
credentials, bounded targets, rollback instructions, and explicit maintainer
approval.

## Apply schedule rules

For every retained schedule:

- declare UTC explicitly or use an intentional IANA timezone and document why
  local civil time matters;
- use a non-zero minute offset unless a vendor requires an hour boundary;
- avoid shared high-load boundaries because scheduled runs can be delayed and,
  under enough load, queued jobs can be dropped;
- bound runtime with timeouts, pagination, and finite retry behavior;
- add safe `workflow_dispatch` input where a maintainer benefits from a
  controlled rerun;
- declare concurrency behavior and whether a newer run should cancel an older
  one;
- name the maintainer or owning team that reviews failures and value.

Scheduled workflows run from the default branch. Confirm the intended
definition is on that branch before relying on the next trigger.

## Review inactivity state

GitHub can automatically disable scheduled workflows in a public repository
after 60 days without repository activity. The API state
`disabled_inactivity` is live state, not evidence that the workflow should be
retired.

Before acting on an inactive schedule:

1. inspect its current workflow state;
2. inspect recent repository and default-branch activity;
3. determine whether new activity would reactivate an obsolete or unsafe
   schedule;
4. classify its purpose and value using the complete record;
5. draft the smallest follow-up under the owning issue.

Do not enable, delete, or rewrite a workflow solely because it is inactive.

## Review failures and value

Group failures by repository, workflow, job, and a stable signature such as the
failing step plus normalized error category. Count occurrences and record the
latest run for each group. Keep transient queue delay distinct from a repeated
deterministic failure.

Refresh live workflow state and the latest runs before describing an old
failure as urgent. Record the observation window and any missing data. A file
on the default branch does not prove execution, and one green run does not
prove continuing value.

Where available, use organization Actions usage and performance metrics to
compare queue time, duration, failure rate, and consumption. Metrics inform a
classification; they do not authorize a change.

## Draft stale and lock dispositions

The default stale and lock policy is `draft-disposition`. Reviews output
candidate lists only. They must not automatically add labels, post comments,
close items, or lock conversations.

Evaluate issues and pull requests separately because their lifecycle signals
and recovery costs differ. Exclude these mandatory categories from routine
stale or lock candidates:

- security reports;
- regressions;
- release blockers;
- roadmap items;
- pinned discussions;
- items labeled `status:blocked`.

A repository-specific exception is allowed only after repository evidence and
explicit maintainer approval identify the alternate criteria, waiting period,
communication, recovery path, and owner.

## Reconcile tracker ownership

Every follow-up has one owning GitHub issue or pull request. Link to that owner
instead of opening duplicates. Use a linked Linear mirror only
for cross-repository, security, release-blocking, strategic, or
organization-infrastructure work.

Before proposing a new tracker item:

1. search the owning repository for an existing issue or pull request;
2. search Linear for a linked or equivalent item;
3. attach new evidence to the existing owner when one exists;
4. record cross-links and keep status, owner, and next step consistent.

## Review the Zsh Plugin Standard twice yearly

The canonical public standard is the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard).
Review it in two planned windows each year. A coordinated `z-shell/wiki` change
must own the schedule, structured review issue, page source, and deterministic
checks. Land that wiki automation before or with any policy change that depends
on an active review cycle. If this runbook lands first, record the wiki work as
an unresolved dependency and do not claim the cycle is active. Do not add a
second scheduled workflow to this repository.

**Authorized exception:** the maintainer approved the wiki-owned workflow to run
unattended twice yearly, execute deterministic read-only checks, and create
exactly one structured review issue with `issues: write`. The issue contains the
draft evidence and classifications for maintainer judgment. This authorization
does not extend to editing the standard, adding labels, posting follow-up
comments, closing or locking items, dispatching other workflows, or changing
repository settings.

The authorized workflow must be idempotent per UTC half-year review window. Use
a stable window key and exact issue title, paginate the complete open and closed
issue set before creation, exclude pull requests, and no-op when any issue
exactly matches that title. Configure concurrency so overlapping scheduled or
manual runs for the same workflow cannot both reach issue creation. Only POST
the issue after the full duplicate lookup finds no match.

### Collect evidence

Use a bounded evidence window and record:

- the current released official Zsh documentation and release notes;
- changes to the canonical wiki page and its open issues or pull requests;
- confirmed behavior and adoption across maintained Z-Shell plugins;
- plugin load, unload, security, compatibility, and performance incidents;
- current documentation and releases for Zi plus at least two other actively
  maintained plugin managers; and
- links, code examples, anchors, and deterministic-check results from the
  coordinated wiki automation once it has landed.

Official Zsh documentation is authoritative for shell semantics. Ecosystem
practice can justify a portable plugin convention, but cannot redefine Zsh.
Manager APIs belong to optional profiles and must not become portable
requirements merely because one sampled manager supports them.

### Classify each reviewed item

Record both dimensions:

```text
Authority: official-zsh | portable-ecosystem | optional-manager-profile
Status: retain | clarify | revise | deprecate | remove
Adoption: established | emerging | legacy | unsupported
Evidence:
Affected examples and links:
Cross-repository impact:
Follow-up owner:
```

Use `established` only when multiple maintained implementations support the
practice. Mark conflicting, obsolete, or unverified behavior explicitly rather
than averaging incompatible manager behavior into a false consensus.

### Complete the review

The structured issue must include:

1. link and anchor verification;
2. native-Zsh validation of runnable examples;
3. internal consistency across terminology, requirements, examples, and
   portable-versus-profile labels;
4. security review of trust boundaries, input handling, network behavior,
   temporary resources, and cleanup;
5. performance review of plugin load paths, repeated work, external processes,
   and completion initialization;
6. manager sampling results without treating manager APIs as shell semantics;
7. cross-repository impact on this repository's policy, scoped instructions,
   patterns, templates, agents, and skills;
8. impact on affected plugin repositories, wiki navigation and automation, and
   the private control workspace's routes and generated composite; and
9. an owner and tracked follow-up for every proposed change.

Deterministic checks provide evidence; maintainers decide normative changes.
Keep the first pass draft-only. A review is complete only when the issue records
the classification, unresolved evidence, cross-repository dependencies, and
whether the next twice-yearly review remains warranted.

## Use draft-only prompt templates

### Scheduled-workflow health review

```text
Review scheduled workflows using live definitions, current workflow state,
recent runs, repository activity, and the recurring-operations classification
record.

- group failures by repository, workflow, job, and stable signature
- count occurrences and record the latest scheduled result
- distinguish queue delay from deterministic failure
- assess observed value rather than file presence
- classify each workflow as retain, event-driven, reusable, manual, or remove
- name an owner, decision evidence, and retirement condition
- keep private evidence in a restricted private artifact
- reconcile each follow-up with its owning GitHub record and any linked Linear mirror

Return a draft only. Do not dispatch, enable, disable, edit, label, comment,
close, lock, or create tracker items.
```

### Stale and lock disposition review

```text
Review issues and pull requests separately under the default
draft-disposition policy.

- use live state and repository-specific evidence
- output candidate lists with age, activity, owner, and recovery context
- exclude security reports, regressions, release blockers, roadmap items,
  pinned discussions, and status:blocked
- identify the existing owning GitHub record and any linked Linear mirror
- state where maintainer judgment is required

Return a draft only. Do not add labels, post comments, close items, lock
conversations, or create tracker items.
```

## Retire recurring work

A workflow is ready for a removal proposal when its input no longer exists,
its outcome is owned by a reliable event-driven or reusable replacement, it
duplicates a canonical service, or repeated evidence shows no useful signal.
The proposal must identify the owner, replacement or reason, rollback path, and
retirement condition. Observe the replacement through its next expected
trigger before removing the old workflow.

A recurring review is ready for retirement when its decision has been made,
its evidence is available through an owning operational process, or several
documented cycles produce no actionable signal. Close or update the owning
tracker records only after reconciliation.

## Verify before, during, and after

### Before

- [ ] Confirm the repository class, default branch, live workflow state, and
      recent repository activity.
- [ ] Identify the owning runbook, GitHub issue or pull request, any linked Linear mirror,
      maintainer, and retirement condition.
- [ ] Classify the operation with the decision tree and complete every record
      field.
- [ ] Separate public-safe evidence from restricted evidence.
- [ ] Review permissions, credentials, immutable references, concurrency,
      timeout, and rollback needs.

### During

- [ ] Keep output draft-only and targets bounded.
- [ ] Record schedules with UTC or an intentional IANA timezone.
- [ ] Group repeated failures by stable signature and retain occurrence counts
      and the latest run.
- [ ] Preserve caller ownership of triggers, permissions, concurrency, and
      target branches when proposing reusable execution.
- [ ] Stop before any mutation or private publication that lacks explicit
      approval.

### After

- [ ] Run repository validation and review the complete diff or draft.
- [ ] Observe the next expected event or scheduled trigger before declaring a
      replacement healthy.
- [ ] Recheck live state after the observation window.
- [ ] Reconcile the owning GitHub record with any linked Linear mirror.
- [ ] Confirm public output contains no private identity, administrative
      detail, credential, secret, local path, or unresolved placeholder.
- [ ] Record whether the workflow or recurring review met its retirement
      criteria.

## Official references

- [GitHub documentation for events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [GitHub documentation for reusing workflow configurations](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
- [GitHub secure use reference for Actions](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub documentation for viewing Actions metrics](https://docs.github.com/en/enterprise-cloud@latest/actions/how-tos/administer/view-metrics)
