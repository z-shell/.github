<!-- GENERATED from knowledge/domains/governance/pull-requests.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# Runbook: Pull requests

Use this runbook for every pull request to a z-shell repository, whoever opens it: a maintainer, a contributor, or an agent. It collects in one place the steps that are otherwise spread across `AGENTS.md`, [ADR-0003](../decisions/0003-conventional-commits.md), [ADR-0022](../decisions/0022-issue-traceability-on-pull-requests.md), [ADR-0026](../decisions/0026-review-triggers-and-fallback.md), [`branch-protection.md`](branch-protection.md), and `.github/workflows/commit-lint.yml`. Where this runbook and one of those disagree, the ADR or the workflow wins; fix the runbook.

## 1. Before the branch

- Read the owning issue and its acceptance criteria. The pull request is measured against them. Complete the [triage procedure](triage.md), including the bounded metadata authorization, before implementation; carry its label and Project 28 verification through opening, review handoff and post-merge.
- Name the branch before creating it. The pattern is the `BRANCH_PATTERN` default in `.github/workflows/commit-lint.yml`:
  - `feature-<issue>`, `bug-<issue>` or `hotfix-<issue>`, optionally followed by a lowercase `-<slug>` (for example `bug-480` or `feature-668-pull-requests`);
  - or `<type>/<lowercase-slug>` with a slash after a Conventional Commits type, or `feature`, `bug` or `hotfix` (for example `docs/pull-requests-runbook`). `docs-488` matches neither and fails the required check.
- A repository may be stricter through the `branch-pattern` input of its commit-lint caller (z-shell/F-Sy-H accepts only `feature|bug|hotfix-<issue>`, with no slug).
- Branch from the repository's base: `main`, except `next` for z-shell/zi ([ADR-0019](../decisions/0019-trunk-on-main-default.md), [`branch-protection.md`](branch-protection.md)). In zi a `hotfix-*` branch may start from and target `main`, must pass zi's main-branch source guard, and is then synchronized into `next` as [`branch-protection.md`](branch-protection.md) describes.

## 2. Opening

- Title and commits follow Conventional Commits ([ADR-0003](../decisions/0003-conventional-commits.md)): `type(scope): description`. `.github/workflows/commit-lint.yml` limits the description to 72 characters, including an issue suffix such as `(#123)`.
- Fill in the repository's pull-request template (the organization default is Summary, Verification, Agent handoff).
- Reference the owning issue in the body ([ADR-0022](../decisions/0022-issue-traceability-on-pull-requests.md)). Use `Closes #N` only when this diff meets every acceptance criterion of #N. Otherwise use `Refs #N`, say which criteria remain, and open or update a follow-up issue. When no issue owns the work, such as gitlink reconciliation, a maintainer (not an agent) applies the `meta:no-issue` label instead.
- When the change departs from what the issue asked for, say so in the body and get the maintainer's agreement before merging. A departure hidden behind `Closes` closes the issue on criteria nobody agreed to.
- Every factual or causal claim in the change and the body is checked, or marked as not yet verified.
- Run the repository's own checks before asking for review, and put the commands and their results under Verification.

## 3. Review

Reviews follow [ADR-0026](../decisions/0026-review-triggers-and-fallback.md).

A repository's `AGENTS.md` may declare automation-only diff classes that need no review of record (ADR-0026 decision 4), limited to changes a machine produced and CI validates in full: gitlink pointer moves in a meta-workspace, the generated-fixture refreshes that go with them, and dependency bumps opened by Renovate or Dependabot. A pull request made only of a declared class skips steps 1 to 4, 6 and 7; any review thread that is opened on it is still handled under step 5. A pull request that touches anything else is reviewed.

1. Unless the maintainer has elected the fallback (step 3), when the head is ready (checks green, body complete) and Copilot review is configured for the pull request's base branch (a `copilot_code_review` rule in the ruleset that governs it), request `copilot-pull-request-reviewer[bot]` once. Confirm the request by a `review_requested` event on the pull request's timeline, created after this request, whose requested reviewer is `Copilot` (the login the timeline shows for the bot); an event for a team or a user, such as a CODEOWNERS request, does not count. Copilot missing from `requested_reviewers` in the response to the request is an early sign that it did not register, not the test. Where the repository, or the pull request's base branch, has no Copilot review configured, the review of record is a human review or a class-eligible maintainer-elected fallback (steps 3 and 4).
2. If the request does not register, the pull request is blocked on review, not ready. The cause is unconfirmed until diagnosed below. In a class 2, 3 or 4 repository (`knowledge/domains/governance/data/repository-classes.yml`) the maintainer may then decide to use the fallback instead of waiting; an agent does not take that decision on its own. Run `.github/skills/code-review/SKILL.md` against `quality/code-review.instructions.md` (the repository's `.github/instructions/` copy, else the z-shell/.github one) on the current head. Post the result as a pull-request review with inline threads for its findings, opening with `Fallback review under ADR-0026: Copilot request not registered on <sha>`. Record the reviewed head, a verdict and evidence for each relevant checklist area, findings and verification limits. A marker or test summary without that review is not a review.
3. A maintainer may elect the fallback up front, without requesting Copilot, in classes 2 to 4. The review then opens with `Fallback review under ADR-0026: maintainer elected, no Copilot request on <sha>` and is executed the same way.
4. Class 1 normally waits for Copilot or a second human. The sole-maintainer exception in [ADR-0035](../decisions/0035-sole-maintainer-class-1-review-exception.md) applies only after that decision is accepted. The maintainer must declare that no second human is available, explicitly elect the exception for the named PR and current head, and record the Copilot request outcome or absence of configuration. A configured request must have failed to register; this is not an up-front Class 1 fallback to save allowance. Require a separate read-only review of the same head, then execute and post the normal fallback review of record with the appropriate ADR-0026 marker. Its visible text records the exception election, separate-review evidence, current-head checks, verification limits and retained recovery plan. A different reviewing session is additional scrutiny, not a second human or proof of independence. The exception does not authorize merge, deployment, image publication or a ruleset bypass. Any new head requires a new election and both reviews.
5. Act on every review thread with a fix, or a reply saying why not. The ruleset requires resolved threads (`required_review_thread_resolution`, [ADR-0013](../decisions/0013-repository-settings-baseline.md)).
6. Batch the thread fixes and push them once before the next Copilot request; that is one round. After the second round in which Copilot raises only implementation-level or wording findings, the maintainer decides whether to defer the rest to an issue instead of requesting a third review.
7. Any push after a fallback review, a rebase included, voids it ([z-shell/.github#664](https://github.com/z-shell/.github/issues/664)). Post a new fallback review on the new head before merging.

### Write a readable fallback review

Keep the exact ADR-0026 opening marker appropriate to the actual request history. Use a short linked commit label elsewhere instead of repeating full hashes. Scale the presentation to the diff: a small fix may need only labeled bullets; a substantive review may benefit from headings and a collapsible evidence section. The example below is a starting point, not a fixed checklist or a substitute for executing the review.

- **Findings first:** state actionable findings by severity, with the exact location, trigger, consequence and remedy. Post inline threads as section 3 requires. When there are no actionable findings, say so directly.
- **Visible decisions and limits:** keep merge blockers, unresolved decisions, self-review status and material verification gaps outside collapsed sections. A short `NOTE` alert can make the self-review limit visible without implying merge approval.
- **Evidence by area:** give each relevant checklist area a verdict and concrete evidence. Use short labeled bullets or paragraphs for explanations; reserve tables for compact comparisons. Do not repair prose-heavy tables with forced line breaks or `<br>` tags.
- **Verification status:** distinguish passed, failed, skipped and unavailable checks. Explain meaningful skips and link source, commit and CI evidence. A passing test suite alone does not prove compatibility, authority or delivery.
- **Optional detail:** use one clearly labeled `<details>` section for lengthy supporting evidence, commands or logs when useful. Keep its conclusions visible. Use fenced code with a language tag for reproducible snippets; choose Markdown features for their purpose rather than decoration.
- **Follow-up:** separate deferred work from current findings and identify its existing issue or proposed owner. Do not imply approval to create or implement further work.

Use one paragraph or list item per source line, with blank lines around headings, lists and Markdown inside `<details>`, following the [documentation instructions](../.github/instructions/documentation/content-placement.instructions.md#line-wrapping). GitHub documents [collapsed sections](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/organizing-information-with-collapsed-sections) and [alerts](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#alerts).

Before posting or updating, check the exact text with GitHub's Markdown renderer and inspect the target review at desktop and narrow widths when available. If rendering cannot be inspected, report that limitation. Send multiline text by file, then verify the stored body and reviewed commit. Reformat an existing review in place only when its evidence, verdict and reviewed HEAD remain unchanged; preserve historical correction comments and request-history records. A new source HEAD requires a newly executed and posted review under ADR-0026, not an edit that carries old evidence forward.

Example for a maintainer-elected fallback without a Copilot request: replace every bracketed placeholder, and use the other opening marker from section 3 when a real request did not register.

```markdown
Fallback review under ADR-0026: maintainer elected, no Copilot request on [full reviewed SHA]

### Findings

[Findings ordered by severity, or "No actionable findings."]

**Scope:** [Latest commit and complete diff reviewed, with an issue or diff link.]

> [!NOTE]
> This is a maintainer-elected self-review, not an independent review or approval to merge.

### Validation

- **Passed:** [Checks and evidence links.]
- **Skipped or unavailable:** [Checks, reasons and their effect on confidence.]

<details>
<summary>Checklist verdicts and supporting evidence</summary>

- **[Relevant area]: [verdict].** [Concrete evidence. Repeat only for relevant areas.]

</details>

### Limits and follow-up

[Material coverage limits, blockers or decisions, and separately recorded follow-up work.]
```

### Diagnose an unregistered request

- Record the request time, repository, base branch, head SHA, request path/reviewer identifier, response and new timeline events. Check for a Copilot review or run as well; another reviewer's event is not confirmation.
- Verify Copilot access and applicable base-branch rules. Compare the request path with a recorded successful Copilot request, or use the documented GitHub reviewer UI and inspect registration. Do not spend repeated review requests merely to diagnose an unknown cause.
- Ask the requester or billing owner to inspect the applicable Copilot usage/allowance and budget/spending-limit page in **Billing and licensing**. Attribute failure to quota only with an explicit exhaustion/limit indication; an empty reviewer list or successful HTTP response alone cannot establish it. GitHub documents usage and budget limits in [About Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review).
- When access, request-path or billing evidence is unavailable, record that gap and say `review request not registered; cause unconfirmed`. Keep private billing details out of public reviews. The maintainer may still elect the class-eligible fallback; no settings or billing change is implied.

## 4. Merge

- All required checks pass on the head, a review of record has posted (unless the whole diff is a declared automation-only class, section 3), and no thread is unresolved. A fallback review of record must be on that same head (section 3, step 7).
- Short-lived topic branches usually squash-merge. Persistent-branch promotion, every zi pull request into `main` (a `hotfix-*` included, since zi's `main` ruleset allows only merge commits), and a zi hotfix synchronization branch that carries a merge commit of `main` into `next` use a merge commit, so the ancestry survives ([`branch-protection.md`](branch-protection.md)). Pass `--match-head-commit <sha>` so a push between checking and merging fails the merge.
- For a squash merge, pass the message explicitly and check it, as [`branch-protection.md`](branch-protection.md) describes for trailers.
- When the body says `Closes #N`, re-check the criteria against the merged diff. If one is not met, reopen #N or open a follow-up at once.
- In zi, a pull request merged into `next` leaves its issue open, because GitHub closes issues only from the default branch. Close those issues by hand when `next` is promoted to `main`, not earlier (zi's `AGENTS.md`).

## 5. After merge

- When the merge closed the issue, confirm that Project 28's built-in workflow moved its item to `Done` ([`project-tracker.md`](project-tracker.md)). In zi the issue item stays open until promotion.
- File the follow-ups promised in the body or in review replies, and link them.
- Delete the branch and any local worktree only with the maintainer's authorization.

## See also

- [`triage.md`](triage.md), for the issue a pull request starts from.
- [`learning-capture.md`](learning-capture.md), for lessons a pull request teaches.
- [ADR-0032](../decisions/0032-organization-procedures-live-once-as-public-runbooks.md), for why procedures like this one live in runbooks.
- [z-shell/.github#668](https://github.com/z-shell/.github/issues/668), for why this runbook exists.
