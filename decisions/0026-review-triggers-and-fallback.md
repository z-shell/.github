# 26. Pull Request Reviews Are Requested Once, Not Billed Per Push, With a Documented Fallback

- **Status:** ACCEPTED
- **Date:** 2026-09-19
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0013](0013-repository-settings-baseline.md) requires Copilot code review in classes 1, 2 and 4 and suggests it in class 3, and `AGENTS.md` makes a pull request done only after every configured review has posted and every thread has been acted on. Neither says when a review is triggered or what happens when Copilot cannot review.

Copilot code review is billed per review from the requesting maintainer's allowance. Seven rulesets set `review_on_push: true` and `review_draft_pull_requests: true` (`z-shell/zi`, `z-shell/.github`, `z-shell/z-a-meta-plugins`, `z-shell/zd`, `z-shell/zsh-eza`, `z-shell/zunit`, `z-shell/zsh-zoxide`), so every push to those repositories bills a review, including pushes to drafts and pushes that only rename a docstring. On 2026-09-19 one maintainer session spent ten reviews across five repositories: two on gitlink-only pull requests in the private meta-workspace, three fix rounds on one policy pull request (rounds two and three were wording), and five on ordinary changes. By the last pull request of the day, `POST /repos/{owner}/{repo}/pulls/{number}/requested_reviewers` returned 200 and the request was never registered: no `review_requested` timeline event, no run, no review. The change was two submodule pointers and one integer, validated by CI; the maintainer merged it by explicit decision, outside any documented bypass, because no policy named one ([z-shell/.github#642](https://github.com/z-shell/.github/issues/642)).

The organization already ships the review procedure Copilot follows: `.github/skills/code-review/SKILL.md` runs `code-review-generic.instructions.md` against the repository contract and produces evidence-based findings. It is used for review-readiness audits and has no standing as a review of record.

## Decision

1. **Reviews are requested, not triggered by pushes.** Every `copilot_code_review` rule sets `review_on_push: false` and `review_draft_pull_requests: false`. The rule's presence per class is unchanged from ADR-0013, and the settings audit continues to check presence only. A review is requested explicitly (`requested_reviewers` with `copilot-pull-request-reviewer[bot]`) when the pull request is ready: checks green, description complete, all local validation run. The request is confirmed on the issue timeline (`review_requested`), not assumed from the API status code.
2. **One request per review round, and the loop is capped.** Thread fixes are batched and pushed once before the next request. After the second round in which Copilot raises only implementation-level or wording findings, the maintainer decides whether to defer the remaining detail to an issue rather than request a third review.
3. **Documented fallback.** When a review request is not registered within the session (no `review_requested` event and no run) the pull request is blocked on quota, not ready. In classes 2, 3 and 4 the maintainer may instead have a review executed under `.github/skills/code-review/SKILL.md` against `code-review-generic.instructions.md` on the current head and post it as a pull request review with inline threads, opening with the line `Fallback review under ADR-0026: Copilot request not registered on <sha>`. That review satisfies the "every configured review has posted" gate and its threads fall under `required_review_thread_resolution` like any other. Class 1 repositories (changes that reach users) wait for Copilot or a second human; the fallback does not apply there.
4. **Automation-only diffs.** A repository may declare in its `AGENTS.md` diff classes that need no review of record, limited to changes a machine produced and CI validates in full: gitlink pointer moves in a meta-workspace, generated-fixture refreshes that accompany them, and dependency bumps opened by Renovate or Dependabot. A pull request that touches anything else is reviewed.

## Consequences

### Positive

- The allowance is spent on reviews of ready heads, so a day of ordinary work no longer ends with a pull request nobody can review.
- The fallback is a named procedure with a marker line, so a merge without Copilot is visible in the record instead of being an undocumented bypass.
- Class 1 keeps its independent second reader.

### Costs and risks

- An agent reviewing its own change shares its blind spots. The fallback is a second pass under the written checklist, not an independent reviewer; that is why class 1 is excluded and why the marker line exists.
- Turning off `review_on_push` removes the review a maintainer never asked for. A pull request that is opened and merged without an explicit request has no review at all; the done gate in `AGENTS.md` still blocks that, and the thread-resolution rule cannot help when there are no threads. The weekly organization review lists merged pull requests without a review of record.
- Seven rulesets change; the change is a parameter edit inside an existing rule and is applied through the ADR-0013 rollout ([z-shell/.github#478](https://github.com/z-shell/.github/issues/478)).

## Alternatives considered

1. **Keep `review_on_push`, buy more allowance.** Rejected: most billed reviews were of heads nobody wanted reviewed (drafts, wording rounds, pointer moves); paying for them does not make them useful.
2. **Make the agent review the review of record everywhere.** Rejected: the independent reader matters most exactly where a change reaches users, and the agent reviewing its own diff is not independent.
3. **No fallback; wait for the allowance to reset.** Rejected: a two-pointer gitlink advance blocked for a day holds every downstream child pin, and the maintainer merged anyway; a rule that is bypassed on the first contact is worse than a narrower rule.

## References

- [z-shell/.github#642](https://github.com/z-shell/.github/issues/642): the decision request, with the 2026-09-19 evidence.
- [ADR-0013](0013-repository-settings-baseline.md): the per-class review requirement this refines; [z-shell/.github#478](https://github.com/z-shell/.github/issues/478): its rollout.
- [ADR-0022](0022-issue-traceability-on-pull-requests.md): traceability the fallback review does not change.
- `.github/skills/code-review/SKILL.md` and `.github/instructions/code-review-generic.instructions.md`: the fallback procedure.
