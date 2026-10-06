# Name and scope agent skills

Apply when creating, renaming, splitting, merging or reviewing a z-shell agent skill. Done when the skill's name, scope and invocation mode pass every rule below and the owning repository's skill checks pass. [Writing for agents](writing-for-agents.md) owns how to write the skill's content; this page owns what one skill covers and what it is called.

## Scope one skill per subject

A subject is a project, tool or artifact that a user names in a request: `zi`, `zunit`, `zd`, `zsh-plugin`. One skill covers the whole subject: creating, maintaining, running, debugging and answering questions about it. Put activity-specific detail in `references/` files that `SKILL.md` names with a loading condition, so the agent reads only the part the task needs.

Do not split a subject by activity when the activities share references. Skills cannot share files, so a split copies the shared material or adds a third skill. One skill per activity also forces several skills to load for one task.

Split off a separate skill only when part of the subject differs in at least one of these ways:

- Invocation mode: one part must run only when the user asks, because it acts on the user's machine, account or published state, while the rest may load automatically. `disable-model-invocation` and `policy.allow_implicit_invocation` apply to a whole skill.
- Authority: one part needs permissions or approvals the rest must not imply.
- Audience: one part serves a different reader, such as plugin users rather than plugin maintainers, with triggers that do not overlap.

A subject's skill that would routinely load irrelevant material, or whose `SKILL.md` would exceed 500 lines after moving detail to references, is a sign of two subjects, not two activities.

Do not create a skill for a tool no z-shell repository uses, or for a task an agent already does correctly without one. Routed instructions, not skills, own cross-cutting requirements such as testing and Zsh scripting rules; a subject's skill links to them.

## Name the skill after its subject

- Use the subject's own name as the skill name: `zi`, `zunit`, `zd`, `zsh-plugin`.
- Add one action suffix only for a part split off under the rules above: `<subject>-<action>`, such as `zi-install`.
- Use the name a user would type in a request. Explain what the subject is in the description, not the name.
- Do not use generic words as the whole name or a suffix: `agent`, `helper`, `tools`, `utils`, `skill`. A skill is not an agent; agent profiles live in `.github/agents/` and may combine several skills.
- Do not add an organization prefix. Plugin installs namespace skills (`/z-shell:zi`); vendored copies rely on the subject name being specific to z-shell.
- Follow the Agent Skills format: 1 to 64 lowercase letters, digits and single hyphens, no leading or trailing hyphen, matching the directory name.

Names carry more weight than their length suggests. When many skills are installed, a runtime may drop descriptions from its skill listing to fit a size budget while keeping every name, so the name alone must identify the subject.

## Write the description for selection

State what the skill covers and when to use it, leading with the subject and the user's likely words. Name the main activities it covers and the tasks that belong to another skill. Keep it under 1024 characters. A user-invoked skill still needs a description, because the user picks it from a menu.

## Rename and retire

Rename only together with a move or another change that already re-pins every consumer: approved revisions, vendored project copies, instruction-surface entries and generated delivery. A rename outside such a change repeats that work for no behavioral gain. Record the old name in the release notes of the repository that publishes the skill.

## Examples

| Request                                                       | Skill        | Why                                                 |
| ------------------------------------------------------------- | ------------ | --------------------------------------------------- |
| Install or update Zi on my machine                            | `zi-install` | Acts on the user's machine; user-invoked            |
| Why does this ice not load?                                   | `zi`         | Model-invoked subject work                          |
| Create a new plugin, or bring an existing one to the standard | `zsh-plugin` | Same subject and references                         |
| Write or run ZUnit tests                                      | `zunit`      | Test framework subject                              |
| Reproduce a Linux failure or benchmark in a container         | `zd`         | Execution environment subject, not a test framework |
| Write Bats tests                                              | none         | No z-shell repository uses Bats                     |

## Sources

Agent Skills [specification](https://agentskills.io/specification) and [best practices](https://agentskills.io/skill-creation/best-practices) (coherent units), Anthropic [skill authoring best practices](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices) (consistent, specific names), Claude Code [skills](https://code.claude.com/docs/en/skills) (listing budget, plugin namespaces, invocation control) and Codex [skills](https://developers.openai.com/codex/skills) (listing budget), checked 2026-10-06.
