# 35. Allow a bounded Class 1 review exception for a sole maintainer

- **Status:** ACCEPTED
- **Date:** 2026-09-27
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

ADR-0026 requires Copilot or a second human for Class 1 repositories. During delivery of the controlled zd runner, the configured Copilot request did not register on the ready head, and the maintainer stated that no other human reviewer is available. Waiting for an unavailable reviewer leaves qualified changes blocked without a usable resolution path. A failed request does not establish quota exhaustion.

This amendment changes only Class 1 fallback eligibility. It preserves ADR-0026's review procedure, current-head evidence, thread resolution and explicit maintainer authority. It takes effect only after maintainer acceptance on main; a proposed policy cannot justify merging a Class 1 PR.

## Decision

1. Class 1 continues to use Copilot or a second human by default. A sole maintainer may elect an exception only when they declare that no second human is available and a configured Copilot request failed to register, or Copilot is not configured for the base branch. Diagnose and record the request under the existing runbook. A registered review that is merely pending is not a failed request. Do not make repeated requests solely to diagnose an unknown cause.
2. The maintainer explicitly elects the exception for a named PR and full current head. An agent cannot infer election from sole ownership, passing checks, silence or general implementation approval. The exception is not an up-front Class 1 fallback to save allowance. A new head voids the election and all fallback evidence.
3. Require an additional read-only review of the exact head in a separate reviewing session. Review source contracts, failure paths, supply-chain boundaries and deployment or image behavior using the organization code-review skill and canonical checklist. Record its findings, evidence and limits. Additional automated scrutiny is not a second human or proof of independent judgment.
4. Execute the normal fallback review of record on that same head and post it as a PR review, with inline actionable findings, using the ADR-0026 marker that matches the actual request history. Keep the sole-maintainer election, separate-review evidence, relevant checklist verdicts, current-head checks, verification gaps and recovery plan visible. Resolve findings and threads before merging. A marker or test summary alone is insufficient.
5. Keep all required checks and ruleset requirements. Do not disable review rules, lower required approvals, bypass thread resolution or use an administrative merge to implement this exception. If a hosted rule requires an unavailable independent approval, that remains a blocker requiring a separately authorized policy/settings decision.
6. Review is separate from merge and publication authority. Class 1 deployment still requires successful build validation on the exact merged main commit. Publish only qualified artifacts from that commit, retain immutable identities and an applicable recovery plan, and report unavailable hosted or platform coverage. The review exception does not authorize deployment, release, image publication, cleanup or account changes.
7. This amends ADR-0026 decision 3 only. Classes 2 to 4, truthful request markers, fresh reviews after a push and automation-only exemptions keep their existing rules.

## Consequences

A sole maintainer gains an explicit, auditable route when the required reviewer is unavailable. Per-head election and two recorded review passes keep the exception deliberate, while functional checks and exact-commit publication requirements remain intact.

The independent second reader is absent. Separate automated review passes can share blind spots, and green tests cannot prove deployment safety. The maintainer accepts that residual risk explicitly; this exception must not be described as an independent approval or an automatic merge permission.

## Alternatives considered

1. Wait indefinitely for Copilot or recruit a second human: retains the strongest default but provides no practical delivery path when neither is available.
2. Allow an up-front Class 1 fallback for every maintainer: simpler, but removes the independent-review default beyond the demonstrated sole-maintainer problem.
3. Merge on green checks without a review of record: loses source review and its evidence, and does not satisfy ADR-0026.
4. Disable the Copilot ruleset or bypass required approvals: changes hosted controls unnecessarily and mixes review policy with account/settings authority.

## References

- [ADR-0026](0026-review-triggers-and-fallback.md), the review procedure amended here.
- [Pull-request runbook](../runbooks/pull-requests.md), request diagnosis, fallback execution and merge verification.
- [Testing instructions](../.github/instructions/testing.instructions.md), Class 1 validation before deployment.
- [zd PR #126](https://github.com/z-shell/zd/pull/126), the controlled-execution prerequisite affected by the unavailable reviewer.
- [Issue #673](https://github.com/z-shell/.github/issues/673), the coordinated quality and performance delivery parent.
