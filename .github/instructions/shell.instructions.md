---
description: "Dispatch shell guidance by the source's actual dialect"
applyTo: "**/*.sh"
---

# Shell Dialect Dispatcher

Classify shell dialect from the actual shebang, invocation, repository contract,
and behavior before applying language rules. Treat `.sh` only as a naming clue.
When evidence conflicts, stop and resolve the dialect instead of importing a
default.

## Zsh

For native Zsh, read
`.github/instructions/zsh-scripting.instructions.md` and
`lib/zsh-standard-policy.json`. Apply its execution profile, compatibility,
syntax, state, and tool boundaries. ShellCheck is not used for Zsh.

## Bash

For Bash, use Bash semantics and declare the supported Bash floor. ShellCheck
may run only with Bash selected explicitly as its dialect. Validate behavior
under the actual Bash versions the repository supports.

## POSIX sh

For POSIX `sh`, limit syntax and builtins to the repository's declared POSIX
environment. ShellCheck may run only with `sh` selected explicitly as its
dialect. Test against the implementations the repository supports.

## Common rules

- Validate untrusted input before interpreting it.
- Avoid unreviewed `eval` and other code re-evaluation.
- Use reliable structured-data parsers instead of ad hoc text splitting.
- Handle critical command and pipeline statuses explicitly.
- Create temporary resources safely and guarantee cleanup.

No shebang, error-option bundle, array model, condition syntax, declaration
builtin, or word-splitting rule is universal across shell dialects. Select each
construct only after declaring the dialect and execution context.
