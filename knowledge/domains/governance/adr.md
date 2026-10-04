# Runbook — ADR drafting

Use this workflow when a discussion, issue, or pull request makes a non-obvious decision that should become durable project memory.

**Hard rule:** draft the ADR, but do not silently mark it accepted. New ADRs start as `PROPOSED` until maintainers confirm them.

## Decision authority

Only an org maintainer may flip an ADR from `PROPOSED` to `ACCEPTED`. Agents and
contributors draft and propose; they never self-accept.

- The maintainer who accepts an ADR records their handle in the `Deciders` field.
  Never leave `Deciders: TBD` on an `ACCEPTED` ADR.
- Acceptance happens on `main` (via merged PR), not on a feature branch.
- Superseding an existing ADR follows the same authority: link the old and new ADRs
  through `Supersedes` / `Superseded by` and leave the superseded ADR in place.

The current accepting maintainer is **ss-o**.

## When to use this

Draft an ADR when:

- a cross-repo policy changes
- a release or compatibility rule becomes explicit
- maintainers choose one non-obvious architectural direction over another
- a repeated "why do we do it this way?" question needs a durable answer

Do not create an ADR for trivia, temporary experiments, or decisions that are still purely exploratory.

## ADR workflow

1. Read the source discussion, issue, or PR carefully.
2. Identify the actual decision, not just the implementation details.
3. Summarize the context, decision, consequences, and alternatives.
4. Number the ADR after the highest existing file in `decisions/`.
5. Set status to `PROPOSED`.
6. Link the source issue, PR, or discussion in `References`.

## Prompt template

```text
Read <issue, discussion, or PR>.

Draft an ADR for z-shell/.github/decisions/ using the existing ADR format in this repository.

Requirements:
- summarize the real decision
- include context, decision, consequences, and alternatives
- status must be PROPOSED
- number it after the highest existing ADR

Draft only. Do not claim it is accepted.
```

## ADR quality checks

- The title states the decision plainly.
- The decision section is actionable and specific.
- The consequences section covers both upside and cost.
- The alternatives are real alternatives, not strawmen.
- The ADR explains why the decision matters to future maintainers.

## See also

- `decisions/`
- `runbooks/org-review.md`
- `.github/AGENT_MEMORY.md`
