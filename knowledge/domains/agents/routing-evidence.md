# Agent routing evidence

Question: how can z-shell group knowledge by domain while preserving supported native entrypoints and selective loading?

Checked: 2026-10-04. This is research evidence, not a replacement policy or a claim of tested runtime behavior. Refresh when a host's discovery contract changes or a migration changes native paths.

| Source | Documented contract | Design implication |
| --- | --- | --- |
| [Agent Skills specification](https://agentskills.io/specification) | Metadata, the selected SKILL.md body and supporting resources load progressively; references should stay focused | Keep skill entrypoints short and conditional detail in directly reachable resources |
| [GitHub repository instructions](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions) | Instruction files may live in subdirectories of .github/instructions; applyTo and excludeAgent control native applicability | Domain instruction directories fit the native contract; preserve selectors and exclusions |
| [GitHub custom agents](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/create-custom-agents) | Repository profiles use .github/agents; organization profiles use root agents/ in the organization's policy repository | Preserve intended audience; existing repository profiles do not prove organization-wide availability |

The domain names and navigation layout are z-shell choices. The organization manifest adds task-and-path selection beyond native path matching. Navigation links are insufficient evidence that a host loaded a mandatory target; validate manifest coverage and observe supported runtime behavior separately.

Open questions: hosted organization-profile availability, native behavior of external-resource links, and runtime context cost after restructuring. None is established by file moves, schema checks or this research page.
