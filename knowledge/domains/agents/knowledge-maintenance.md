# Maintain central knowledge

Shared migrated organization content has one editable source under knowledge/domains/ in z-shell/.github. Domain indexes select relevant sources. knowledge/delivery.json maps each source to its complete generated consumer. Publication locations and native runtime entrypoints remain usable without depending on optional skills or link-following behavior.

## Change an existing source

1. Select the domain and inspect the delivery map for the source and all consumers. Read the applicable policy and source before editing.
2. Correct the source against current project evidence or official documentation. Preserve rule IDs, exceptions, compatibility floors, authority and required applicability. Changing placement does not prove that inherited content is accurate.
3. Run python3 automation/knowledge/knowledge-delivery.py, then its --check mode. Generated consumer edits are rejected by the check.
4. Run applicable policy, routing, language-contract and project checks. Verify Markdown links at both source and consumer paths. Report unavailable hosted discovery separately.

Markdown links are rebased during delivery. Repository-relative paths in commands and prose retain their repository-root meaning. Native frontmatter remains with its source and is preserved in the generated instruction or profile. The generator adds provenance after frontmatter.

## Preserve complete consumers

Generated delivery is a maintained interface, not an independently editable source. The current 55 entries have these consumer contracts:

| Consumers | Reason to retain complete delivery |
| --- | --- |
| AGENTS.md | Standalone mandatory organization baseline under ADR-0014 |
| PATTERNS.md | Shared implementation guidance linked by the baseline and selected instruction routes |
| 14 .github/instructions/ files | Manifest selection and native scoped frontmatter; preserve task and path selectors, exclusions and stable rule IDs |
| 22 runbooks/ files | Public procedures reached by skills, manifests and contributor links under ADR-0032 |
| Three .github/agents/ profiles | Repository-native role discovery and complete profile content; organization scope is not yet verified |
| .github/AGENT_MEMORY.md | Handoff guidance used by the baseline and native issue form |
| Nine .github/ community documents | Existing policy and community-file interfaces; custom governance documents do not gain default inheritance merely by placement |
| .github/README.md and three actions/ README files | Repository and action documentation at their existing public presentation paths |

Do not classify these files as removable duplicates solely because they are generated. Before proposing retirement of an exact consumer, identify its manifest routes, native discovery or presentation role, skills and templates, workflow inputs, local links and published downstream references. Verify the complete replacement in standalone use and each supported runtime where mandatory content is affected. An unobserved runtime remains an unresolved prerequisite, even when static checks pass.

Retirement then needs an approved exact removal scope, coordinated source publication and downstream migration. Update delivery.json and repository-files.json with that removal, repair local references, regenerate resource pages and run affected checks together. Keep existing consumers when any dependency or replacement loading behavior is unverified. Never replace mandatory content with a pointer whose target the host has not been shown to load.

## Migrate additional knowledge

### Complete project instructions

knowledge/project-delivery.json extends the existing organization-routing pipeline for complete project-native scoped instructions. Each consumer must already be declared for its repository in .github/instruction-surfaces.json. Its preserved quoted applyTo selector must match that surface's comma-separated file_patterns. Task selectors continue to come from the routing manifest.

Each version 1 consumer record has exactly these fields:

| Field | Contract |
| --- | --- |
| repository, source, target | Declared downstream repository, editable knowledge/domains/ Markdown source and complete .github/instructions/ consumer |
| revision, source_blob | Approved organization commit and its exact regular-file Git blob, each a full 40-character lowercase hexadecimal identifier |
| project_revision, project_source_blob | Tested project revision and original instruction blob, each a full 40-character lowercase hexadecimal identifier |
| content_sha256 | SHA-256 of the complete rendered consumer bytes, including frontmatter and provenance |

The approved organization revision must be an ancestor of the checked-out tooling revision. Render from its committed blob, never the dirty authoring file. Organization-relative Markdown links become immutable organization revision links. Links explicitly pinned to the tested project revision become consumer-relative project links; other remote links remain unchanged. Native frontmatter is retained and provenance follows it.

Publish and approve the organization source before adding a delivery record and replacing project authoring ownership. Record the project compatibility checks with the owning work item before approving its project_revision and project_source_blob. Those two fields preserve the asserted reconciliation baseline; the organization verifier does not independently fetch that project or prove its runtime behavior.

Run org-routing.py validate for schema and declarations, and verify-approved with full organization Git history for source reachability, blob identity, rendering digest and selectors. The existing apply command prepares all selected approved consumers and validates paths and selectors before writing the routing block or consumers. It preserves repository content outside the routing block; selected complete consumers are generated interfaces. The check command compares complete consumer bytes and selectors without needing organization source history, so it works with the reusable workflow's sparse tooling checkout.

Missing consumers, changed rules, frontmatter or provenance, invalid pins, inconsistent selectors and symlink paths fail these checks. Preflight failures prevent writes; apply does not provide a multi-file rollback for an operating-system failure during writing. A passing static check establishes the declared byte contract, not project compatibility, native discovery or hosted adoption. The manifest remains empty until coordinated source publication and consumer approval are available.

Follow [repository placement and maintenance](repository-layout.md) when allocating policy data, templates, programs, tests and native delivery. The repository file inventory rejects retired allocation directories and undeclared automation domains.

Inventory the existing owner, audience, source revision, consumers, required routes and validation contracts. Reconcile duplicate or inaccurate content before replacing its owner. Add a source and delivery entry together, verify coverage, and update the domain index.

Move simple local documents when their complete delivery and reference repairs can be verified together. For cross-repository content, generated pages, source-derived internals or accepted ownership changes, record the remaining migration in the relevant project's issue or workspace note. Keep the original owner active until replacement delivery is verified. Do not silently create an independently editable copy.

Every tracked or non-ignored organization repository file outside knowledge/ has a disposition in [the repository inventory](../../repository-files.json): imported with its editable source, referenced with its domain reading context, or awaiting a deletion decision. Historical ADRs, executable configuration, native skills, implementation, tests and assets retain their actual owners and are referenced rather than rewritten as prose. Add or update the disposition when a file changes ownership, appears or is removed. Run python3 automation/knowledge/knowledge-coverage.py --write to regenerate domain resource pages, then run it without --write to check coverage and drift. These checks establish placement and discoverability, not accuracy of inherited claims.

If a file has neither relevant knowledge to import nor a useful retained role to reference, present its exact path, consumer evidence and deletion consequences to the maintainer. Do not delete it without explicit approval. Keep pending decisions visible in the inventory.

Wiki migrations need MDX/frontmatter/component, anchor, build and publication checks. Project-local migrations need revision compatibility, native instruction selection and standalone delivery checks. Approved pins and published links are updated only after the new source is available.

Architecture changes are recorded in proposed ADRs; existing accepted decisions keep their historical status. Public knowledge excludes runtime credentials, private bindings and maintainer agreements.
