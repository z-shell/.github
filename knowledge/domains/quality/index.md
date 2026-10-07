# Quality

Select this domain for testing, code review, controlled reproduction or benchmark evidence. Read the owning project's checks before selecting an execution environment.

| Task | Authoritative context |
| --- | --- |
| Choose tests by repository class | [Testing contract](testing.md) |
| Review changes | [Review criteria](code-review.md), [review skill](../../../.github/skills/code-review/SKILL.md) and [review readiness](org-review.md) |
| Select independent verification | [Verification escalation](independent-verification.md) |
| Reproduce in a controlled environment | [Controlled validation](controlled-validation.md), [zd runbook](zd-validation.md) and [`zi-docker` skill](https://github.com/z-shell/agent-skills/blob/main/plugins/z-shell/skills/zi-docker/SKILL.md) |
| Report benchmark evidence | [Benchmark runbook](benchmark-report.md) and [ADR-0024](../../../decisions/0024-benchmarks-observed-not-gated.md) |

Distinguish syntax, functional behavior, platform coverage and timing. Review evidence is tied to the assessed revision; [PR review requirements](../governance/pull-requests.md) govern delivery.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.
