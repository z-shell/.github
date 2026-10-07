---
description: "Route generic review and README tasks on plugin-shaped files to the canonical Zsh plugin guidance"
applyTo: "**/*.plugin.zsh,**/init.zsh,knowledge/domains/documentation/templates/zsh-plugin.md,.github/agents/zsh-plugin-reviewer.agent.md"
---

<!-- GENERATED from knowledge/domains/plugins/review-routing.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# Zsh Plugin Standard Task Aliases

For plugin-shaped code, plugin scaffolding, and the plugin README template,
apply the mandatory
[Zsh Plugin Standard instructions](standard-selection.instructions.md).
The canonical public standard remains the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard),
and official Zsh documentation remains authoritative for shell semantics.

Generic `code-review` and `readme-authoring` tasks do not imply that every Zsh
file or README is a plugin. Apply this route only to the plugin-specific paths
declared in this instruction's `applyTo` scope.
