---
name: github-issues
description: Read, draft, create, or update GitHub issues with runtime capability discovery, exact authorization boundaries, and verification of every external write.
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
