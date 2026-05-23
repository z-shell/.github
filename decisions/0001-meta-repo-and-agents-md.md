# 1. Adopt a meta-repo pattern centered on `AGENTS.md`

- **Status:** PROPOSED
- **Date:** 2026-05-19
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

The z-shell organization spans many repositories with a small maintainer group responsible for triage, releases, documentation, templates, workflows, and cross-repo coordination.

Until now, conventions and decisions have been split across:

- individual repository READMEs
- commit history and pull-request context
- GitHub Discussions and issues
- local LLM memory and ad hoc prompts

That creates predictable failure modes:

- cross-repo conventions drift
- new maintainers and LLM agents re-derive the same answers
- recurring workflows are executed differently each time
- org-level changes fan out slowly and inconsistently

At the same time, `AGENTS.md` has emerged as a common cross-tool entry point for coding-agent instructions, while GitHub-native files in `.github` already serve as the default organization health and workflow hub.

## Decision

Adopt `z-shell/.github` as the canonical meta-repository for organization-wide agent instructions, ADRs, runbooks, patterns, templates, and shared GitHub workflow assets.

The top-level structure is:

```text
AGENTS.md                 canonical org-wide agent instructions
CLAUDE.md                 thin Claude entry point to AGENTS.md
PATTERNS.md               cross-repo implementation idioms
decisions/                architectural decision records
runbooks/                 repeatable operational workflows
.github/                  default community files and GitHub-native workflow assets
```

Rules:

- `AGENTS.md` stays short and operational.
- `decisions/` is append-only; supersede with a new ADR instead of rewriting history.
- `PATTERNS.md` records only patterns already observed in at least two repositories.
- `runbooks/` must be executable, not aspirational.
- Active progress lives in issues, PRs, and the tracker, per `.github/AGENT_MEMORY.md`.

## Consequences

### Positive

- One canonical place for "how this org works"
- Shared entry point for human maintainers and AI coding agents
- Better cross-repo consistency for workflows, templates, and decisions
- Reviewable, versioned institutional memory

### Negative / costs

- Initial migration and curation effort
- Ongoing discipline required to keep docs current
- Risk of drift if files become aspirational instead of grounded in real work

### Neutral

- Repository-specific instructions can still exist where the local workflow is meaningfully different.
- Long-form user documentation still belongs in the wiki where practical.

## Alternatives considered

1. **Status quo:** rejected because conventions and context already drift.
2. **Wiki-only governance:** rejected because ADRs, templates, and agent instructions benefit from pull-request review and repo-local discoverability.
3. **Per-repo-only instructions:** rejected because org-level guidance would be duplicated across many repositories.
4. **One giant file for everything:** rejected because decisions, runbooks, and patterns evolve differently and should not be mixed.

## References

- `AGENTS.md`
- `.github/AGENT_MEMORY.md`
- `PATTERNS.md`
