# CI

Select this domain for GitHub Actions authoring, review, workflow changes and shared CI callers.

| Task | Authoritative context |
| --- | --- |
| Author or review a workflow | [Workflow contract](workflow-contract.md) and [naming decision](../../../decisions/0005-workflow-naming-conventions.md) |
| Use an author or reviewer role | [Workflow author](roles/ci-workflow-author.md) or [workflow reviewer](roles/ci-workflow-reviewer.md) |
| Manage dependency updates | [Dependency management](dependency-management.md) |
| Audit scheduled organization automation | [Recurring operations](../governance/recurring-operations.md) |
| Use maintained action documentation | [Setup Zsh](setup-zsh-action.md), [commit action](commit-action.md) and [rclone action](rclone-action.md); verify inherited examples against the actual action and current workflow contract |

Role profiles are optional entrypoints. Required permissions, pinning, concurrency and verification come from the canonical contract and project checks. Use [quality](../quality/index.md) for test selection and [governance](../governance/index.md) for publication gates.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.
