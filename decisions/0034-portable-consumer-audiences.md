# 34. Use portable audiences for shared instruction surfaces

- **Status:** ACCEPTED
- **Date:** 2026-09-27
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

ADR-0014 inventories instruction surfaces with `consumers`, while ADR-0032 requires verified delivery per runtime. Shared surfaces enumerate Codex, Claude Code, Copilot and Gemini CLI, excluding Hermes and Antigravity despite their use in maintainer workflows. Repeating runtime names on portable policy and skills makes each new runtime or product transition require edits across unrelated surfaces.

The field has several current uses: audience inventory, duplicate-route identity and exact runtime adapter validation. Downstream routing generation uses tasks, paths and approved vendored skills, not the consumer list. Intended audience and observed runtime delivery must remain distinct.

## Decision

1. Keep `consumers` required. Add `agent` as the portable coding-agent audience, alongside `human` and `ci` as applicable.
2. Use portable audiences for shared policy, runbooks and portable skills. Keep concrete runtime identifiers for adapters and runtime-specific guidance. Do not broaden targeted guidance without assessing its actual mechanics.
3. Preserve existing concrete identifiers and manifest version 1 for compatibility. Keep the existing exact adapter contracts; generic `agent` cannot substitute for an adapter's concrete consumer.
4. Audience declarations do not prove runtime discovery, installation or invocation, change task/path routing, or authorize actions. Delivery remains separately verified per runtime under ADR-0014 and ADR-0032.
5. Migrate the canonical public portable surfaces first. Coordinate private validator and inventory changes separately before claiming the maintainer workspace has adopted the audience model. Do not rename or remove Gemini delivery as a side effect of adopting Antigravity.

## Consequences

Portable surfaces include current and future coding agents without repeated runtime-list maintenance. Runtime adapters retain explicit, reviewable loading contracts. Existing named consumers remain valid, so the schema extension does not invalidate older declarations.

Older validators reject `agent`; inventories must be paired with a compatible validator revision. Private delivery and downstream installations are separate rollout steps, and static audience coverage cannot be reported as tested runtime support.

## Alternatives considered

1. Add Hermes and Antigravity to every shared list: smaller schema change, but repeats this maintenance whenever runtimes change.
2. Replace every consumer with `agent` and `human`: loses adapter specificity and the distinct automated-check audience.
3. Remove `consumers`: loses audience inventory and weakens adapter checks without improving delivery verification.
4. Add a new audience field and runtime registry: clean separation, but duplicates metadata and introduces migration machinery unnecessary for the current inventory model.

## References

- [ADR-0014](0014-portable-agent-instruction-architecture.md), [ADR-0031](0031-per-repository-instruction-routing-delivery.md), [ADR-0032](0032-organization-procedures-live-once-as-public-runbooks.md).
- [Instruction update runbook](../runbooks/instruction-update.md#consumer-audiences).
- [Issue #668](https://github.com/z-shell/.github/issues/668), shared instruction delivery and reference integrity.
- [Google's Gemini CLI transition announcement](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/), which retains enterprise and paid API access.
