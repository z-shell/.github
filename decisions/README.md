<!--
GENERATED FILE. DO NOT EDIT DIRECTLY.
Regenerate: python3 scripts/decision-records.py
Check: python3 scripts/decision-records.py --check
-->

# Architecture decision records

Durable organization decisions. Draft new records with `runbooks/adr.md`; only
a maintainer moves a record from `PROPOSED` to `ACCEPTED`.

| ADR                                                     | Title                                                               | Status   | Date       | Deciders |
| ------------------------------------------------------- | ------------------------------------------------------------------- | -------- | ---------- | -------- |
| [0001](0001-meta-repo-and-agents-md.md)                 | Adopt a meta-repo pattern centered on `AGENTS.md`                   | ACCEPTED | 2026-05-29 | ss-o     |
| [0002](0002-zi-as-canonical-plugin-manager.md)          | `zi` is the canonical plugin manager for the z-shell ecosystem      | ACCEPTED | 2026-05-29 | ss-o     |
| [0003](0003-conventional-commits.md)                    | Adopt Conventional Commits across z-shell repositories              | ACCEPTED | 2026-05-29 | ss-o     |
| [0004](0004-dependabot-unification.md)                  | Standardize on Dependabot for Dependency Management                 | ACCEPTED | 2026-05-20 | ss-o     |
| [0005](0005-workflow-naming-conventions.md)             | No Emojis in Workflow and Job Name Fields                           | ACCEPTED | 2026-05-21 | ss-o     |
| [0006](0006-wiki-content-root-boundaries.md)            | Wiki Content-Root Boundaries                                        | ACCEPTED | 2026-05-29 | ss-o     |
| [0007](0007-release-publication-flow.md)                | Release and Publication Flow                                        | ACCEPTED | 2026-05-26 | ss-o     |
| [0008](0008-branching-model.md)                         | Branching Model                                                     | ACCEPTED | 2026-07-25 | ss-o     |
| [0009](0009-testing-ci-strategy.md)                     | Testing and CI Strategy                                             | ACCEPTED | 2026-07-25 | ss-o     |
| [0010](0010-security-incident-response.md)              | Security Incident Response                                          | PROPOSED | 2026-05-29 | TBD      |
| [0011](0011-zsh-lint-semantic-analyzer-architecture.md) | zsh-lint Conditional Semantic Analysis Pipeline                     | ACCEPTED | 2026-07-25 | ss-o     |
| [0012](0012-hybrid-dependency-management.md)            | Split Dependency Updates Between Renovate and Dependabot            | ACCEPTED | 2026-06-21 | ss-o     |
| [0013](0013-repository-settings-baseline.md)            | Repository Settings Baseline by Class                               | ACCEPTED | 2026-07-25 | ss-o     |
| [0014](0014-portable-agent-instruction-architecture.md) | Adopt portable agent-instruction delivery                           | ACCEPTED | 2026-07-23 | ss-o     |
| [0015](0015-zsh-scripting-standard.md)                  | Adopt an organization-wide Zsh scripting standard                   | ACCEPTED | 2026-08-27 | ss-o     |
| [0016](0016-promotion-trigger-criteria.md)              | Next-to-Main Promotion Trigger Criteria                             | ACCEPTED | 2026-08-16 | ss-o     |
| [0017](0017-licensing-standard-by-provenance.md)        | Licensing Standard by Provenance and Consumption                    | ACCEPTED | 2026-08-18 | ss-o     |
| [0018](0018-portable-worktree-management.md)            | Adopt Portable Worktree Management                                  | ACCEPTED | 2026-08-27 | ss-o     |
| [0019](0019-trunk-on-main-default.md)                   | Trunk-on-Main Default with a Zi Integration Exception               | ACCEPTED | 2026-08-28 | ss-o     |
| [0020](0020-adopt-zsh-plugin-standard-2.md)             | Adopt Zsh Plugin Standard 2 as a Clean Portable Contract            | ACCEPTED | 2026-08-28 | ss-o     |
| [0021](0021-derive-chroma-knowledge-at-runtime.md)      | Derive Chroma Command Knowledge at Runtime                          | ACCEPTED | 2026-08-29 | ss-o     |
| [0022](0022-issue-traceability-on-pull-requests.md)     | Enforce Issue Traceability on the Pull Request, Not the Branch Name | ACCEPTED | 2026-09-02 | ss-o     |
