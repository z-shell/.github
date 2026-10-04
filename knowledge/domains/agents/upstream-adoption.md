# Upstream skill selection

Reviewed the current [Matt Pocock skills catalog](https://github.com/mattpocock/skills/tree/main/skills) on 2026-10-04. Selection is adapted guidance inside z-shell knowledge management, not an installation of the upstream collection. Catalog entries were screened by description and dependency references; selected workflows and their relevant supporting formats were read in full.

| Selected upstream material | z-shell implementation | Conditional relationship |
| --- | --- | --- |
| domain-modeling, GLOSSARY-FORMAT and ADR-FORMAT | [Domain modeling](domain-modeling.md), [glossary](glossary.md) | Clarification and planning select domain modeling when terms or ownership change |
| research | [Knowledge research](knowledge-research.md) | Modeling, clarification and planning select research for missing primary evidence |
| writing-for-agents and SKILL-MECHANICS | [Writing for agents](writing-for-agents.md) | Research-to-guidance conversion and authoring select this procedure |
| grill-with-docs and its grilling dependency | [Decision clarification](decision-clarification.md) | Combines terminology work with questions about consequential choices |
| wayfinder, to-spec and to-tickets | [Migration planning](migration-planning.md) | Research and clarification resolve prerequisites before synthesis and consumer batches |
| retro | [Learning capture](../governance/learning-capture.md) and [writing for agents](writing-for-agents.md) | Review existing checks and navigation before proposing evidence-backed maintenance changes |
| ask-matt | The operation-selection table below and z-shell-knowledge-management routing | Select only the branch needed for the requested outcome |

## Operation selection

| Requested outcome | Read |
| --- | --- |
| Define domains or resolve vocabulary | Domain modeling |
| Verify or refresh a knowledge claim | Knowledge research |
| Author or refactor agent-consumed content | Writing for agents |
| Settle consequential unresolved choices | Decision clarification |
| Plan cross-project or compatibility-sensitive migration | Migration planning |
| Review reusable learning before completion | Existing learning-capture procedure |

These dependencies are conditional reading routes. They do not require runtime-specific Skill-tool calls or a new skill for every reference. Standard z-shell implementation and verification procedures remain applicable throughout.

## Selection limits

The upstream engineering setup, tracker labels, docs/adr layout, branch orchestration and publication actions are not adopted. z-shell already owns those contracts. Codebase-design, architecture improvement, TDD, implementation, bug diagnosis and PR production belong to their existing engineering workflows or later developer-skill work. Prototyping and teaching are selected only for an explicit need, not required by knowledge maintenance.

In-progress writing and runtime-handoff skills, TypeScript migrations, course scaffolding and hook installers are outside this knowledge migration. Exhaustive questioning, automatic tracker changes, fixed one-ticket-per-session limits and avoiding precise paths would conflict with this workspace's authorized execution and evidence needs.

For retrospective review, z-shell retains its mandatory learning-capture owner and implementation-time policy checks. Apply the useful upstream review of navigation, tooling cost and unwired checks without introducing a second learning procedure or making mandatory policy review-only.

Refresh the selection when upstream dependencies, runtime mechanics or z-shell's ownership contracts change. [Recorded blob revisions](upstream-provenance.json) identify selected skills and supporting references. [Upstream MIT license](upstream-license.txt) retains the source notice. Mutable main links alone are not revision pins.
