---
description: "Route generic review and README tasks on plugin-shaped files to the canonical Zsh plugin guidance"
applyTo: "**/*.plugin.zsh,**/init.zsh,templates/readme/zsh-plugin.md,.github/skills/new-zsh-plugin/**,.github/agents/zsh-plugin-standard-reviewer.agent.md"
---

# Zsh Plugin Standard Task Aliases

For plugin-shaped code, plugin scaffolding, and the plugin README template,
apply the mandatory
[Zsh Plugin Standard instructions](zsh-plugin-standard.instructions.md).
The canonical public standard remains the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard),
and official Zsh documentation remains authoritative for shell semantics.

Generic `code-review` and `readme-authoring` tasks do not imply that every Zsh
file or README is a plugin. Apply this route only to the plugin-specific paths
declared in this instruction's `applyTo` scope.
