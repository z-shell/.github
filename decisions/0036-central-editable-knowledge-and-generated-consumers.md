# 36. Central Editable Knowledge With Complete Generated Consumers

- **Status:** PROPOSED
- **Date:** 2026-10-04
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

Organization knowledge is spread between native instructions, runbooks, role profiles and project documentation. Navigation helps discovery but leaves authoring fragmented. The maintainer requested that migrated public knowledge have one editable home, with maintained consumers at the locations where people and runtimes need it.

ADR-0014 requires a standalone organization baseline and mandatory delivery. ADR-0032 requires public procedures and thin skill routers. Centralizing editable sources must preserve those guarantees. Existing accepted decisions retain their historical status; adoption of this proposal will need coordinated ownership updates where their authoring-location wording changes.

## Decision

1. Author migrated public knowledge under knowledge/domains/ in z-shell/.github. Give each source a primary subject domain. Domain indexes link directly to maintained source content.
2. Declare complete generated consumers in knowledge/delivery.json. Keep AGENTS.md, scoped native instructions, public runbooks and repository-local roles usable at their supported locations. Generated consumers contain provenance and are checked against their source.
3. Preserve authority, applicability, compatibility, rule IDs and required runtime delivery. A skill or navigation link cannot be the only delivery of mandatory policy.
4. Migrate cross-repository content only with its consumer contract: wiki MDX and builds, project revision compatibility, native routing and approved pins. Until a coordinated migration completes, its existing owner remains authoritative and the migration is tracked in the relevant issue or workspace note.
5. Keep architectural decisions as historical records in decisions/. Keep private bindings and agreements out of public knowledge. Knowledge ownership and maintenance are independent of skill marketplaces.

## Ownership transition and delivery limits

This proposal changes the editable authoring location of migrated material, not its mandatory delivery or historical decision identities. ADR-0014's baseline remains complete in AGENTS.md; ADR-0031's manifest and downstream routing retain their ownership and approved-revision boundaries; ADR-0032's public runbooks remain complete procedure consumers, with one editable source declared in knowledge/delivery.json. Maintainer acceptance must explicitly reconcile the earlier decisions' authoring-location wording. Their recorded statuses and supersession metadata are not changed by local implementation of this proposal.

Numbered ADRs retain their existing editable owner in decisions/. Domain navigation references them without creating generated copies; automation/governance/decision-records.py alone generates decisions/README.md. A source-location exception for historical records preserves their header, numbering and acceptance contract.

Generated consumers are retained interfaces. Their removal is not part of this proposal's local implementation: each retirement needs verified replacement delivery, a consumer inventory, coordinated publication and separately approved deletion. Repository profiles remain at .github/agents/ until organization-wide scope and native discovery are verified. Independent modules retain their module and build contracts during knowledge organization.

## Consequences

One editable source removes manually maintained copies. Existing consumer locations remain compatible, while deterministic checks detect drift. The physical copies remain generated delivery rather than separate authoring stores.

Generation adds a required maintenance check. Cross-repository publication and supported runtime behavior still need explicit verification. Moving inherited text alone does not establish accuracy, and project-derived guidance still needs a tested revision.

## Alternatives considered

1. Keep distributed editable owners and add indexes. This improves navigation but leaves the maintainer's authoring problem unresolved.
2. Replace every native consumer with a link. This depends on unverified link-following behavior and can hide mandatory context.
3. Move every project document at once. This couples source ownership changes to unverified builds, anchors and project compatibility.

## References

- [Tracking issue 717](https://github.com/z-shell/.github/issues/717).
- [Knowledge maintenance](../knowledge/domains/agents/knowledge-maintenance.md).
- [ADR-0014](0014-portable-agent-instruction-architecture.md).
- [ADR-0032](0032-organization-procedures-live-once-as-public-runbooks.md).
