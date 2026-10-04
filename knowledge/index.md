# z-shell knowledge domains

Find the authoritative context for the current task. Start with [organization policy](../AGENTS.md) and select required guidance through the [instruction manifest](../.github/instruction-surfaces.json). These indexes provide navigation; reading an index does not load its linked resources or replace manifest selection.

| Domain | Select for |
| --- | --- |
| [Zsh](domains/zsh/index.md) | Language semantics, source profiles, compatibility and shell dialects |
| [Zi](domains/zi/index.md) | Plugin-manager behavior, annex interfaces and installation |
| [Plugins](domains/plugins/index.md) | Portable plugin scaffolding, configuration and lifecycle |
| [Modules](domains/modules/index.md) | Compiled modules, ABI and build/runtime boundaries |
| [Tooling](domains/tooling/index.md) | Parsers, analyzers and supplemental-tool limitations |
| [CI](domains/ci/index.md) | GitHub Actions authoring, review and reusable workflows |
| [Quality](domains/quality/index.md) | Tests, review, controlled validation and benchmarks |
| [Documentation](domains/documentation/index.md) | Content placement, authoring, READMEs and accessibility |
| [Governance](domains/governance/index.md) | Repository operations, worktrees, decisions and delivery |
| [Agents](domains/agents/index.md) | Context selection, instruction routing and runtime integrations |

Choose one primary domain and additional domains only when the task crosses their boundaries. A Zsh plugin change normally selects Zsh, plugins and applicable quality guidance. A Go parser change selects tooling and quality; it needs Zsh semantics only for the language behavior being analyzed. A workflow change selects CI and its repository's tests.

Migrated policy, guidance, procedures and role content is authored in these domain directories. The [delivery map](delivery.json) declares complete generated consumers at native instruction, agent and runbook paths. Follow [knowledge maintenance](domains/agents/knowledge-maintenance.md) when editing or migrating content. [ADRs](../decisions/README.md) retain their historical records. Project-specific contracts and wiki content retain their current owners until their coordinated migrations are complete.

When knowledge changes, update its existing owner and repair these links. Capture reusable research only when existing code, decisions or documentation do not already explain it. Record the question, scope, primary evidence, checked revision/date, uncertainty and refresh condition. Optional navigation and research never become the sole delivery of mandatory instructions.

For remaining repository files, each domain's repository-resources page states when to read the file, why it retains its native location, or which imported source owns its delivery. The [file disposition inventory](repository-files.json) is checked by python3 automation/knowledge/knowledge-coverage.py. Coverage includes supporting assets and fixtures; it does not imply that every file is agent guidance.
