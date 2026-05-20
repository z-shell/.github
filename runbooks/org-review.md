# Runbook — Weekly org review

Use this workflow to turn organization-wide GitHub activity into a short prioritized draft for maintainers.

**Hard rule:** this workflow produces a draft only. Do not label, comment, close, merge, or file follow-up issues automatically unless a maintainer explicitly asks for that as a separate step.

## Goal

Create a one-pass weekly review that answers:

- what changed across the organization in the last 7 days
- what needs attention now
- which issues or PRs appear to be part of the same cross-repo pattern
- which follow-up items should be proposed to maintainers

## Inputs

- GitHub issues and pull requests across the z-shell organization
- relevant tracker items
- recent workflow failures where they materially affect maintainer priority

## Output shape

Return a draft with these sections:

1. **Urgent**
2. **Needs review**
3. **Cross-repo patterns**
4. **Suggested follow-ups**

Each item should link the source issue, PR, or workflow and explain why it matters in one sentence.

## Review steps

1. Summarize new issues opened in the last 7 days by repository.
2. List PRs waiting for review longer than 3 days.
3. Flag regressions, security issues, or release blockers.
4. Look for repeated symptoms or the same maintenance task across multiple repositories.
5. Suggest the smallest useful follow-up action for each important item.

## Prompt template

```text
Using GitHub tools, review the last 7 days across the z-shell organization.

- summarize new issues by repository
- flag regressions, security-sensitive issues, and release blockers
- list PRs waiting for review for more than 3 days
- identify repeated patterns across repositories
- suggest a prioritized maintainer action list

Output sections:
1. Urgent
2. Needs review
3. Cross-repo patterns
4. Suggested follow-ups

Do not act. Draft only.
```

## Follow-up discipline

- If the review suggests a non-trivial new task, propose a GitHub issue in the owning repository.
- If an item is already tracked, link it instead of duplicating it.
- If the review exposes a recurring rule or process gap, propose a `PATTERNS.md`, ADR, or runbook update.

## See also

- `runbooks/triage.md`
- `runbooks/adr.md`
- `.github/AGENT_MEMORY.md`
