# Zsh

Select this domain before reading, diagnosing, reviewing or changing Zsh semantics. Establish the actual dialect, execution profile and repository compatibility floor first.

| Task | Authoritative context |
| --- | --- |
| Classify a shell source | [Dialect selection](dialect-selection.md) |
| Apply the organization Zsh contract | [Scripting rules](scripting.md) and [machine-readable policy](../../../knowledge/domains/zsh/data/zsh-standard-policy.json) |
| Resolve language behavior | [Released official Zsh manual](https://zsh.sourceforge.io/Doc/Release/index.html) and [manual research workflow](../../../.github/skills/zsh-manual-research/SKILL.md) |
| Understand organization standard ownership | [ADR-0015](../../../decisions/0015-zsh-scripting-standard.md) |

Use [plugins](../plugins/index.md) for plugin-specific contracts and [tooling](../tooling/index.md) for parser limitations. Native syntax evidence and runtime behavior are separate; the owning project's commands determine the needed verification.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.

Structured policy owned by this domain:

- [zsh-standard-policy.json](data/zsh-standard-policy.json)
