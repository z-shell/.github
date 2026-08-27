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

- Write Zsh-first code; do not substitute Bash syntax or portability advice for
  documented Zsh behavior.
- Namespace plugin-owned functions, parameters, aliases, hooks, widgets, and
  other mutable shell state.
- Scope option changes with `emulate -L zsh` or save and restore the prior
  option state when a change must outlive one function call.
- Make load-time side effects explicit, minimal, and documented.
- When the plugin declares an unload contract, provide lifecycle cleanup that
  reverses plugin-owned side effects, including hooks, functions, parameters,
  aliases, widgets, path entries, and temporary resources.
- Do not perform network activity during plugin load. Network access must be an
  explicit user action.
- Validate syntax with native Zsh. When unload is part of the contract, exercise
  load and unload behavior in a clean Zsh process.

## Portable requirements and manager profiles

Keep portable plugin requirements separate from optional plugin-manager
profiles. Manager APIs such as Zi metadata, `PMSPEC`, or a manager-maintained
plugin registry may improve integration, but they are not portable Zsh
requirements. Use them only behind an intentional profile or capability guard,
and never present one manager's API as shell semantics.

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
