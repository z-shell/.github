---
description: "Canonical Z-Shell requirements for authoring, changing, documenting, and reviewing Zsh plugins"
applyTo: "**"
---

# Zsh Plugin Standard Instructions

The canonical public plugin-authoring standard is the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard).
Read the current page before creating, changing, documenting, or reviewing a
Zsh plugin. Link to it instead of copying its full rules into repositories,
templates, reviews, or agent guidance.

Official Zsh documentation remains authoritative for shell syntax, expansion,
options, builtins, and other language semantics. If the standard, a plugin
manager, or an example conflicts with the Zsh manual for the supported Zsh
version, follow the manual and report the documentation drift.

## Organization requirements

- Treat version 2 as one clean portable contract. Do not preserve an older
  namespace, shared registry, configuration parameter, or directory convention
  merely as a compatibility path in a refactored plugin.
- Choose and document one portable ASCII project identifier. Derive every
  persistent public or private shell-visible name from it, using a leading
  underscore for private state and callbacks.
- Use one project-owned `zstyle` context for ordinary public configuration.
  Keep project parameters private and do not expose scattered configuration
  globals or environment variables as a parallel interface.
- Portable code must neither require nor mutate a shared manager or plugin
  registry parameter. Manager integration belongs to an optional, independently
  tested profile.
- Write Zsh-first code; do not substitute Bash syntax or portability advice for
  documented Zsh behavior.
- Namespace plugin-owned functions, parameters, aliases, hooks, widgets, and
  other mutable shell state.
- Scope option changes with `emulate -L zsh` or save and restore the prior
  option state when a change must outlive one function call.
- Make load-time side effects explicit, minimal, and documented.
- Provide idempotent lifecycle cleanup that tolerates partial initialization
  and reverses plugin-owned side effects, including hooks, functions,
  parameters, aliases, widgets, path entries, and temporary resources. Restore
  prior state only while the installed value remains unchanged; preserve newer
  user state.
- Do not perform network activity during plugin load. Network access must be an
  explicit user action.
- Validate syntax with native Zsh. Separately exercise the declared load
  surface, repeated source, partial failure, hostile caller state, and exact
  unload behavior in a clean Zsh process.

## Portable requirements and manager profiles

Keep portable plugin requirements separate from optional plugin-manager
profiles. Manager APIs such as Zi metadata or `PMSPEC` may improve integration,
but they are not portable Zsh requirements. Use them only behind an intentional
profile or capability guard, never mutate a manager-owned registry from the
portable entrypoint, and never present one manager's API as shell semantics.

Zi is the Z-Shell reference manager for examples and testing under
`decisions/0002-zi-as-canonical-plugin-manager.md`. This affects defaults, not
the definition of portable plugin behavior.

## Review output

Identify whether each finding is:

1. an official-Zsh semantic error;
2. a portable Plugin Standard violation;
3. an optional manager-profile defect; or
4. a repository-specific convention.

Do not fail portable compliance solely because an optional manager integration
is absent.
