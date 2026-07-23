# Z-Shell Agent Memory Protocol

Z-Shell uses GitHub-native records as the shared memory between humans and LLM agents. Local LLM memory is useful as a cache, but it is never the source of truth for organization progress.

## Sources of Truth

| State                                    | Source of truth                                               |
| ---------------------------------------- | ------------------------------------------------------------- |
| Active work, blockers, and next steps    | GitHub issues, pull requests, and the Z-Shell Tracker project |
| Deferred or planned work                 | GitHub issues in the owning repository                        |
| Durable decisions and long-form guidance | Z-Shell wiki                                                  |
| Local agent recall                       | Optional cache only; must not be the only record              |

## Agent Workflow

Before starting non-trivial work:

1. Search the owning repository for open issues and pull requests related to the task.
2. Check linked tracker items and previous handoff comments.
3. Prefer the most recent GitHub-visible state over local notes or LLM memory.
4. If no issue exists for planned or deferred work, create one in the owning repository.

While working:

1. Keep progress attached to the relevant issue or pull request.
2. Update the thread when status changes materially, especially when work becomes blocked.
3. Link branches, pull requests, CI runs, and follow-up issues instead of relying on prose-only status.

Before stopping or handing off:

1. Leave a handoff comment on the owning issue or pull request when work is unfinished, blocked, or non-trivial.
2. Include verification that was actually run.
3. Include exact next steps that a fresh agent or maintainer can execute without guessing.
4. Convert deferred work into tracker issues instead of leaving it only in a handoff.

## Handoff Comment Format

Use this structure for issue and pull request comments:

```markdown
## Agent handoff

**Status:** In progress | Blocked | Ready for review | Complete
**Repository:** z-shell/<repo>
**Branch/PR:** <branch and/or PR link>
**Tracker/Issue:** <issue or tracker link>

### Current state

- <what is true now>

### Verification

- <command or check>: <result>

### Blockers

- <blocker or "None">

### Next steps

1. <next concrete action>
2. <next concrete action>
```

## Rules

- Do not store secrets, credentials, private hostnames, private IP addresses, personal local paths, or machine-specific state.
- Do not create repo-local memory logs unless that repository has a specific, documented need.
- Do not use a central append-only Markdown file for active progress; it will drift and conflict.
- Keep durable documentation in the wiki and link to it from repository-local files when needed.
- Keep the tracker issue body or PR thread concise, factual, and actionable.
