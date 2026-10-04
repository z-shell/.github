# 26. Pull Request Reviews Are Requested Once, Not Billed Per Push, With a Documented Fallback

- **Status:** ACCEPTED
- **Date:** 2026-09-19
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0013](0013-repository-settings-baseline.md) requires Copilot code review in classes 1, 2 and 4 and suggests it in class 3, and `AGENTS.md` makes a pull request done only after every configured review has posted and every thread has been acted on. Neither says when a review is triggered or what happens when Copilot cannot review.

Copilot code review is billed per review from the requesting maintainer's allowance. Seven rulesets set `review_on_push: true` and `review_draft_pull_requests: true` (`z-shell/zi`, `z-shell/.github`, `z-shell/z-a-meta-plugins`, `z-shell/zd`, `z-shell/zsh-eza`, `z-shell/zunit`, `z-shell/zsh-zoxide`), so every push to those repositories bills a review, including pushes to drafts and pushes that only rename a docstring. On 2026-09-19 one maintainer session spent ten reviews across five repositories: two on gitlink-only pull requests in the private meta-workspace, three fix rounds on one policy pull request (rounds two and three were wording), and five on ordinary changes. By the last pull request of the day, `POST /repos/{owner}/{repo}/pulls/{number}/requested_reviewers` returned 200 and the request was never registered: no `review_requested` timeline event, no run, no review. The change was two submodule pointers and one integer, validated by CI; the maintainer merged it by explicit decision, outside any documented bypass, because no policy named one ([z-shell/.github#642](https://github.com/z-shell/.github/issues/642)).

The organization already ships the review procedure Copilot follows: `.github/skills/code-review/SKILL.md` runs `quality/code-review.instructions.md` against the repository contract and produces evidence-based findings. It is used for review-readiness audits; only its execution and posted review under the procedure below have standing as a fallback review of record.

The amendment proposed in [#664](https://github.com/z-shell/.github/issues/664) records the maintainer decisions of 2026-09-26: an up-front fallback election in classes 2 to 4, a review of record even when Copilot is not configured, and a new review after any push. It also distinguishes a failed request from a confirmed usage limit. Existing correction comments on the ten reviews identified in #664 remain the historical record; do not rewrite those reviews to imply a request occurred.

## Decision

1. **Reviews are requested, not triggered by pushes.** Every `copilot_code_review` rule sets `review_on_push: false` and `review_draft_pull_requests: false`. The rule's presence per class is unchanged from ADR-0013, and the settings audit continues to check presence only. Unless the maintainer elects the fallback below, a configured Copilot review is requested explicitly (`requested_reviewers` with `copilot-pull-request-reviewer[bot]`) when the pull request is ready: checks green, description complete, all local validation run. The request is confirmed by a new `review_requested` timeline event identifying Copilot, not assumed from the API status code or an unrelated reviewer event.
2. **One request per review round, and the loop is capped.** Thread fixes are batched and pushed once before the next request. After the second round in which Copilot raises only implementation-level or wording findings, the maintainer decides whether to defer the remaining detail to an issue rather than request a third review.
3. **Review of record and maintainer-elected fallback.** Every non-exempt pull request needs a posted review of record, whether or not Copilot review is configured for its base branch. In classes 2, 3 and 4 the maintainer may elect a fallback up front, when Copilot is not configured, or after a request fails to register. An agent never elects it on the maintainer's behalf. Class 1 normally waits for Copilot or a second human. [ADR-0035](0035-sole-maintainer-class-1-review-exception.md) defines the accepted bounded sole-maintainer exception.

   A fallback is executed under `.github/skills/code-review/SKILL.md` against `quality/code-review.instructions.md` on the current head and posted as a pull-request review, with inline threads for actionable findings. Record the reviewed head, relevant checklist verdicts and evidence, findings, and verification limits; a marker or test summary alone is not a review. Use the marker matching what occurred:
   - Maintainer election without a Copilot request: `Fallback review under ADR-0026: maintainer elected, no Copilot request on <sha>`.
   - A real request did not register: `Fallback review under ADR-0026: Copilot request not registered on <sha>`.

   An unregistered request blocks review readiness, but does not establish quota exhaustion. Confirm registration and diagnose the cause using `runbooks/pull-requests.md`; without billing/limit evidence report the cause as unconfirmed. The fallback satisfies the review-of-record gate, and its threads fall under `required_review_thread_resolution`. Any push after the fallback, including a rebase, voids it: execute and post a new review on the new head before merge. No review of one's own change is an approval to merge.

4. **Automation-only diffs.** A repository may declare in its `AGENTS.md` diff classes that need no review of record, limited to changes a machine produced and CI validates in full: gitlink pointer moves in a meta-workspace, generated-fixture refreshes that accompany them, and dependency bumps opened by Renovate or Dependabot. A pull request that touches anything else is reviewed.

## Consequences

### Positive

- The allowance is spent on reviews of ready heads, so a day of ordinary work no longer ends with a pull request nobody can review.
- The fallback is a named procedure with a marker line, so a merge without Copilot is visible in the record instead of being an undocumented bypass.
- Class 1 normally keeps its independent second reader; ADR-0035 separately records the sole-maintainer exception and its added risk.

### Costs and risks

- An agent reviewing its own change shares its blind spots. The fallback is a second pass under the written checklist, not an independent reviewer; that is why Class 1 normally requires Copilot or a second human and why the marker line exists. ADR-0035 describes the additional limits for a sole-maintainer exception.
- Turning off `review_on_push` removes the review a maintainer never asked for. A pull request that is opened and merged without an explicit request has no review at all; the done gate in `AGENTS.md` still blocks that, and the thread-resolution rule cannot help when there are no threads. The weekly organization review lists merged pull requests without a review of record.
- Seven rulesets change; the change is a parameter edit inside an existing rule and is applied through the ADR-0013 rollout ([z-shell/.github#478](https://github.com/z-shell/.github/issues/478)).

## Alternatives considered

1. **Keep `review_on_push`, buy more allowance.** Rejected: most billed reviews were of heads nobody wanted reviewed (drafts, wording rounds, pointer moves); paying for them does not make them useful.
2. **Make the agent review the review of record everywhere.** Rejected: the independent reader matters most exactly where a change reaches users, and the agent reviewing its own diff is not independent.
3. **No fallback; wait for the allowance to reset.** Rejected: a two-pointer gitlink advance blocked for a day holds every downstream child pin, and the maintainer merged anyway; a rule that is bypassed on the first contact is worse than a narrower rule.

## References

- [z-shell/.github#664](https://github.com/z-shell/.github/issues/664): amendment discussion and recorded maintainer decisions.
- [Pull-request runbook](../runbooks/pull-requests.md): request diagnosis and review execution.
- [z-shell/.github#642](https://github.com/z-shell/.github/issues/642): the decision request, with the 2026-09-19 evidence.
- [ADR-0013](0013-repository-settings-baseline.md): the per-class review requirement this refines; [z-shell/.github#478](https://github.com/z-shell/.github/issues/478): its rollout.
- [ADR-0022](0022-issue-traceability-on-pull-requests.md): traceability the fallback review does not change.
- `.github/skills/code-review/SKILL.md` and `.github/instructions/quality/code-review.instructions.md`: the fallback procedure.
