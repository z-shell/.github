---
name: github-issues
description: Investigate, assess, read, draft, create, or update GitHub issues with current-state verification, value-versus-cost analysis, runtime capability discovery, and exact write boundaries.
---

# GitHub Issues

Use GitHub issues as the authoritative record for active and deferred work.
Project 28 is a portfolio view, and Linear is only a selective linked mirror.

## Authority boundary

- Reading, searching, and drafting are read-only.
- Creating or changing an issue, comment, label, assignee, milestone, issue
  type, relationship, project item, or status is an external write and requires
  explicit user authority for that exact mutation.
- Do not infer write authority from a request to investigate, triage, plan, or
  draft.
- Project membership and Linear mirroring are separate mutations.

This boundary applies to every command and reference included with this skill.

## Discover capabilities

Discover available MCP, app, and CLI tools at runtime. Do not assume a named
server or tool is installed. For GitHub CLI, inspect the installed contract:

```sh
gh --version
gh issue --help
gh issue <command> --help
```

Use a high-level command when the installed version supports the required
field. Current GitHub CLI versions may support issue types directly through
`gh issue create --type`; verify with `gh issue create --help`. Use `gh api`
only for capabilities the installed high-level command does not expose.

## Investigation workflow

For z-shell work, follow the routed canonical `runbooks/triage.md`. This skill
owns the operational procedure, not disposition policy.

1. Resolve the issue and its live state, project fields, dependencies, and
   blockers.
2. Fetch the current target branch, record its exact commit, and inspect the
   current source instead of trusting a stale checkout.
3. Search related issues, pull requests, commits, ADRs, and accepted patterns.
4. Trace the affected implementation and its callers. Reproduce the behavior
   or record the evidence gap, then run the smallest meaningful checks.
5. Compare expected user, correctness, security, performance, and maintenance
   value with implementation cost, regression risk, and ongoing ownership.
6. Recommend exactly one disposition: implement, defer, close as completed,
   close as not planned, or request more information.

Structure the report as: recommendation and disposition, current reality and
history, confirmed finding, value versus cost, verification and evidence gaps,
and the next authorized action. Investigation does not authorize a tracker
write.

## Read or draft workflow

1. Resolve the owner, repository, issue number, and current state.
2. Search for an existing owner before proposing a new issue.
3. Read applicable templates, labels, issue types, and dependency context.
4. Draft the exact title and body without writing externally.
5. Report the proposed mutation and wait for explicit authority when none was
   provided.

## Authorized write workflow

1. Re-read the target immediately before mutation.
2. Confirm the approved fields and exclude adjacent changes.
3. Put multiline text in a temporary body file, reject literal `\\n`
   placeholders, and use `--body-file` or an equivalent file-input endpoint.
4. Perform only the approved write.
5. Read the stored issue or comment back and verify its exact fields and
   rendered line breaks.
6. Report the resulting URL.

## Pull-request issue links

Closing keywords create a Development link only when the pull request targets
the repository's default branch. If repository policy requires a non-default
base, preserve that base and create a manual closing reference after explicit
authority. Do not retarget the pull request merely to activate the keyword. A
manual link does not change GitHub's default-branch requirement for closing the
issue.

Prefer a discovered high-level capability. If none exists, confirm the current
GraphQL schema exposes `addCloseIssueReferences` with `issueId` and
`pullRequestIds`, then use the issue and pull-request node IDs:

```sh
gh api graphql \
  -f query='mutation($issueId: ID!, $pullRequestIds: [ID!]!) { addCloseIssueReferences(input: {issueId: $issueId, pullRequestIds: $pullRequestIds}) { issue { number } } }' \
  -f issueId='ISSUE_NODE_ID' \
  -F 'pullRequestIds[]=PR_NODE_ID'
```

Keep the complete `pullRequestIds[]=...` field quoted in Zsh so `NOMATCH` does
not reject it before `gh` runs. Read both `closedByPullRequestsReferences` on
the issue and `closingIssuesReferences` on the pull request back after the
mutation.

Never expose tokens, use destructive issue operations without exact authority,
or treat tool availability as permission.

## References

Load only the reference needed for the request:

- `references/templates.md`: issue body structure
- `references/search.md`: search syntax
- `references/issue-types.md`: issue type discovery
- `references/issue-fields.md`: dates, priority, and custom fields
- `references/dependencies.md`: blocking relationships
- `references/sub-issues.md`: parent and child issues
- `references/projects.md`: Project 28 fields and membership
- `references/images.md`: authorized image attachment workflow
