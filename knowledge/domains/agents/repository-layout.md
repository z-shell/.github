# Repository placement and maintenance

The maintainer approved the local layout refactor on 2026-10-04. Publication, downstream adoption, ADR acceptance and deletion of compatibility consumers remain separate decisions. Track implementation and evidence in [migration status](migration-status.md).

## Allocate by responsibility

| Material | Editable owner or native interface |
| --- | --- |
| Organization knowledge and researched procedures | knowledge/domains/<domain>/ |
| Structured organization policy | The owning domain's data/ directory |
| Executable maintenance components | automation/<domain>/ with adjacent tests and component fixtures |
| Historical decision records | Existing decisions/ owns numbered records; domain indexes reference them and decision-records.py owns the generated index |
| GitHub workflows, community defaults, instructions and skills | Their documented native locations; generate complete consumers where the delivery map declares sources |
| Organization-wide agent profiles | Root agents/ when organization scope and discovery are verified; repository-only profiles stay in .github/agents/ |
| Published actions and action documentation | Stable actions/ interfaces; documentation is generated from declared knowledge sources |
| Organization profile and workflow starters | Native profile/ and workflow-templates/ locations |
| Independent terminal-demo Go module | Retain tools/readme-terminal-demo during the initial refactor; tool retirement or module relocation requires its own verified batch |

Automation domains in this batch are agents, knowledge, governance and ci. They identify operational responsibility, not programming language. Python, Ruby and shell keep their existing runtime and compatibility targets. Preserve language-native test conventions; do not reorganize a Go internal package solely to match a script layout.

## Historical decisions and current guidance

Numbered records in decisions/ remain editable historical owners, not generated knowledge consumers. Their identity, acceptance metadata, supersession links and evidence belong to the record. The decision-record validator discovers decisions/NNNN-*.md and requires the title and metadata at the beginning of each file; the knowledge generator's leading provenance header does not satisfy that contract. Domain indexes and the file inventory reference the records without importing a second editable copy. decisions/README.md is generated only by automation/governance/decision-records.py.

The authoring transition is described in proposed [ADR-0036](../../../decisions/0036-central-editable-knowledge-and-generated-consumers.md), rather than rewriting accepted decisions as though they had always used knowledge/domains/. Its adoption needs maintainer acceptance. [ADR-0014](../../../decisions/0014-portable-agent-instruction-architecture.md) requires the complete standalone baseline; [ADR-0031](../../../decisions/0031-per-repository-instruction-routing-delivery.md) owns downstream routing and approved skill delivery; [ADR-0032](../../../decisions/0032-organization-procedures-live-once-as-public-runbooks.md) owns public procedures and thin skill routers. The local source migration preserves those delivery guarantees. Acceptance must reconcile their authoring-location wording without changing historical status or implying that downstream adoption occurred.

## Independent tool and agent scope

tools/readme-terminal-demo declares module github.com/z-shell/.github/tools/readme-terminal-demo, Go 1.26 and toolchain go1.26.5. Its CLI and tests import that module's internal packages. Its Dockerfile uses the module directory as build context, copies go.mod and go.sum, and runs module-local tests, vet and build. Retaining the module directory preserves those contracts; a move into automation is not equivalent to relocating a standalone maintenance script. This is source inspection, not evidence that its renderer, container or sandbox ran successfully.

The three generated profiles currently target .github/agents/, and their name and description frontmatter remains part of delivery. They are repository profiles. Organization delivery through root agents/ requires a separate audience decision, matching native discovery evidence and updates to the manifest, inventory and generation targets. Neither role prose nor the public repository's name proves organization-wide discovery.

## Required maintenance rules

1. Give each new file an authoritative owner, concrete reading or execution purpose and an inventory disposition. Generic scripts/ and lib/ are not new allocation targets after their migrations pass.
2. Keep implementation, affected tests and fixtures in the same component or automation domain. Shared imports crossing domains use explicit module paths; never rely on accidental caller working directories.
3. Resolve the repository root through an explicit CLI root or validated layout markers. Verify worktrees, non-Git exports, non-interactive execution and sparse checkout contracts before changing path resolution.
4. Keep generated consumer paths in the delivery manifest, preserve native frontmatter and mandatory content, and run both generation and drift checks. Edit the source instead of maintaining a duplicate.
5. Update imports, CLI examples, workflow path filters, sparse-checkout inputs, fixture loaders, policy manifests and resource references together. Published pins remain tied to their actual source revisions.
6. Validate the affected component offline first, then the relevant integration contracts. Separate local checks from hosted runtime discovery and downstream rollout evidence.
7. Preserve historical decision identities and statuses. Reference repairs do not accept an ADR or prove a policy's current operational accuracy.
8. Retire compatibility consumers only after their known dependencies are accounted for and deletion is explicitly approved. Never replace a substantive required consumer with an unverified pointer.
