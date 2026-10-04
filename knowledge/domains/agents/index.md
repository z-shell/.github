# Agents

Select this domain for context selection, instruction changes, runtime integration and agent-role design.

| Task | Authoritative context |
| --- | --- |
| Select required context | [Context routing](context-routing.md) and [instruction manifest](../../../.github/instruction-surfaces.json) |
| Change instructions and their consumers | [Instruction-update procedure](instruction-update.md) and [portable architecture](../../../decisions/0014-portable-agent-instruction-architecture.md) |
| Understand downstream routing and pins | [ADR-0031](../../../decisions/0031-per-repository-instruction-routing-delivery.md) and [approved revisions](../../../knowledge/domains/agents/data/approved-skills.json) |
| Select optional runtime integrations | [Tool integration](tool-integration.md) |
| Check current loading and placement evidence | [Routing research](routing-evidence.md) |
| Maintain editable sources and delivery | [Knowledge maintenance](knowledge-maintenance.md) and [delivery map](../../delivery.json) |
| Define boundaries and terminology | [Domain modeling](domain-modeling.md) and [knowledge glossary](glossary.md) |
| Verify evidence and write maintained guidance | [Knowledge research](knowledge-research.md) and [writing for agents](writing-for-agents.md) |
| Resolve choices and coordinate migrations | [Decision clarification](decision-clarification.md) and [migration planning](migration-planning.md) |
| Review adopted upstream workflows | [Selection and dependency report](upstream-adoption.md) |
| Check rollout coverage and unresolved owners | [Migration status](migration-status.md) |
| Allocate repository content and maintain automation | [Repository layout rules](repository-layout.md) |

Keep required policy, optional skills and host-specific roles distinct. A valid manifest or present profile is not proof of discovery, invocation or correct execution. Resolve native host contracts before asserting portability.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.

Structured policy owned by this domain:

- [approved-skills.json](data/approved-skills.json)
