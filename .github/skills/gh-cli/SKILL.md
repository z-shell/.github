---
name: gh-cli
description: Use GitHub CLI safely by discovering the installed version and command capabilities, defaulting to read-only inspection, and requiring explicit authority for every external write.
---

# GitHub CLI

Use the installed `gh` CLI as a capability-discovered interface, not as a
version-pinned command catalog.

## Safety boundary

- Default to read-only commands.
- Require separate explicit user authority before creating, editing, closing,
  deleting, merging, releasing, dispatching, pushing, or changing repository,
  organization, project, or account settings.
- A request to inspect or diagnose does not authorize a write.
- Never run commands that print authentication tokens or secret values. Use
  `gh auth status` to inspect authentication without exposing credentials.
- Do not use an authentication failure during a network outage as proof that a
  credential is invalid.
- Do not use force, admin, destructive, or bypass flags unless the user has
  explicitly authorized that exact action and target.
- A local commit does not authorize a push, pull request, merge, release, or
  deployment.

## Discover current capabilities

Before relying on syntax or flags:

```sh
gh --version
gh help
gh <group> <command> --help
```

Use the help output from the installed version as the command contract. For
REST or GraphQL behavior, consult current official GitHub documentation and
inspect the endpoint or schema before constructing a request.

## Read workflow

1. Resolve the repository and exact target.
2. Check authentication with `gh auth status` when authentication matters.
3. Inspect the installed command's help.
4. Run the narrowest read-only query.
5. Report the source URL or stable identifier with the result.

Prefer structured output when supported:

```sh
gh <group> <command> --help
gh <group> <command> --json <fields> --jq '<expression>'
```

Do not assume every command supports `--json`, `--jq`, pagination, sorting, or
the same flags as another command.

## Write workflow

After explicit external-write authority:

1. Re-resolve the repository, target, and current state.
2. State the exact mutation and its recoverability.
3. Recheck the installed command's help.
4. For multiline issue, pull-request, release, or comment text, write the exact
   body to a temporary file, reject literal `\\n` placeholders, and use
   `--body-file` or the endpoint's file-input equivalent.
5. Perform only the approved mutation.
6. Read the stored object back and verify the changed fields.

Do not broaden a narrow approval into adjacent labels, assignments, project
changes, repository settings, branch operations, or publication actions.

## Fallbacks

- Prefer a supported high-level `gh` command when it exposes the required field.
- Use `gh api` only when the installed high-level command lacks the capability.
- Discover optional MCP or app tools at runtime. Their presence does not change
  the authorization boundary.
- If current documentation or network access is unavailable, stop before a
  mutation rather than guessing command syntax.
