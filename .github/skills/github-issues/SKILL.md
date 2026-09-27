---
name: github-issues
description: Triage, investigate, draft, create or update GitHub issues using the organization triage runbook and current GitHub capabilities.
---

# GitHub Issues

Read the routed canonical `runbooks/triage.md` before acting. If it is unavailable locally, read the [public triage runbook](https://github.com/z-shell/.github/blob/main/runbooks/triage.md). That runbook owns the investigation, disposition, authorization and metadata procedure; this skill is its entry point. If neither source is accessible, report the gap and do not perform external writes.

- Resolve the owning repository, issue and current evidence before selecting the relevant runbook steps and supporting references.
- Apply the runbook's authority checks, including reuse of an explicitly approved delivery scope. Tool availability never supplies authority.
- Discover installed MCP, app or CLI capabilities. Inspect `gh --version` and the relevant command's `--help`; prefer supported high-level commands.
- For authorized multiline writes, use a body file, reject literal `\n` placeholders and pass `--body-file` or equivalent file input. Read stored fields back and follow the runbook's progress and handoff requirements.

## References

Load only the reference needed for the request:

- [templates](references/templates.md): issue body structure
- [search](references/search.md): search syntax
- [issue types](references/issue-types.md): issue type discovery
- [issue fields](references/issue-fields.md): dates, priority and custom fields
- [dependencies](references/dependencies.md): blocking relationships
- [sub-issues](references/sub-issues.md): parent and child issues
- [projects](references/projects.md): Project 28 fields and membership
- [images](references/images.md): authorized image attachment workflow
- [issue links](references/issue-links.md): manual closing-reference command mechanics
