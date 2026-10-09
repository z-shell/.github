# 40. Central Project Profiles for Issue Intake

- **Status:** PROPOSED
- **Date:** 2026-10-09
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

Most issues in the organization are filed through the API by the maintainer account and its agents. The triage runbook's "Filing a new issue" section makes such an issue mirror the effective issue form, and the organization bug form is now project-neutral. Neither can ask what a project needs to reproduce a bug: Zi's ices, annexes and load phase; zpmod's compiler, CMake and vendored Zsh headers; F-Sy-H's theme, terminal and other ZLE plugins; zsh-lint's invocation, configuration and report kind. Those facts were scattered across READMEs, contributing guides and maintainer memory, or absent. An audit of the organization's issue intake on 2026-10-08 recommended central per-repository profiles, and the maintainer chose to keep them in this repository.

GitHub issue forms cannot be conditional, and any file in a repository's `.github/ISSUE_TEMPLATE/` hides every organization form. A profile-specific form therefore means vendoring the whole form set into the repository. Agents, the dominant filing path, read `AGENTS.md`, which already carries the generated `org-routing` block of [ADR-0031](0031-per-repository-instruction-routing-delivery.md).

## Decision

1. Each project profile lives in `knowledge/domains/governance/data/project-profiles.json`, keyed by a repository declared downstream in `.github/instruction-surfaces.json`. A profile records the component name, how a user reports the installed version, the development branch, the Zsh floor, the tested Zsh versions and platforms, install methods, verification commands, the extra bug-report fields, and the commit and date the facts were read at.
2. `automation/agents/org-routing.py` validates the profiles with the inventory and renders a `Reporting issues` section inside the repository's `org-routing` block. This extends ADR-0031 point 2: besides routing, the block carries project intake facts that no repository-owned text states. It still restates no organization policy, which it links to.
3. The block renders only intake facts: the version command or note, a pointer to "Filing a new issue", and the extra `### ` headings. Branch, Zsh versions, install and test commands stay in the profile for later consumers, because the repositories already state them in their own text and a second copy would compete with it.
4. Delivery follows ADR-0031. A repository receives the section when it repins the Org Routing workflow to a revision carrying its profile and regenerates its block in a reviewed change of its own. Nothing here writes to another repository.
5. Generated issue forms, and a check that compares a profile's tested versions with the repository's CI, are later steps that need their own change.

## Consequences

- Web and agent filings converge on the form's headings plus the profile's fields, and the project facts gain one editable home.
- Profiles go stale unless someone rereads them. The recorded revision and date show their age, and the stated versions are not yet compared with CI.
- Every block regeneration for a profiled repository now includes the section, so editing a profile changes generated text in that repository after its next repin.

## Alternatives considered

1. Profiles in each repository: closer to the code, but would need a collector and does not match the central knowledge model of [ADR-0036](0036-central-editable-knowledge-and-generated-consumers.md).
2. Hand-maintained repository forms: uneven coverage, facts duplicated across contributing guides and forms, and nothing reaches the 76 repositories without forms.
3. Render every profile field into `AGENTS.md`: duplicates the branch, version and test text the repositories already own.

## References

- [Triage runbook: Filing a new issue](../runbooks/triage.md#filing-a-new-issue).
- [ADR-0031](0031-per-repository-instruction-routing-delivery.md).
- [ADR-0036](0036-central-editable-knowledge-and-generated-consumers.md).
