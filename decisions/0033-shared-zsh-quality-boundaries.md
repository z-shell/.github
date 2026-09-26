# 33. Shared Zsh Quality Integrations Keep Analysis and Workloads Repository-Owned

- **Status:** PROPOSED
- **Date:** 2026-09-26
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

The organization already has a reusable Zsh lint workflow, duplicated consumer integrations, and independent benchmark suites. Centralizing execution can reduce maintenance, but an organization-wide wrapper must not claim that parser coverage proves native validity or that instrumentation represents ordinary project performance. Initiative [#673](https://github.com/z-shell/.github/issues/673) coordinates an incremental rollout.

## Decision

1. `z-shell/zsh-lint` owns parsing, rules, configuration, suppressions and diagnostic contracts. `z-shell/.github` owns the reusable CI integration. Consumers own reviewed source inventories, execution profiles, compatibility floors and functional tests.
2. Shared lint runs the complete selected project. Enrollment requires explicit project configuration, proven parser compatibility, positive and negative tests, and recorded workflow and analyzer release pins. Observation is explicitly named and cannot turn invocation errors or incomplete analysis into successful quality evidence.
3. Native syntax, compilation and functional checks remain independent. Broad enforcement waits for exact native-oracle qualification; a valid native construct is not rewritten merely to satisfy an incomplete parser. Required-check names and trigger coverage are verified per repository before changing settings.
4. ADR-0024 remains the performance policy. Workloads and correctness assertions remain in their owning repositories. Shared infrastructure validates and presents the versioned reports; timings flag review, while broken behavior and invalid measurements fail.
5. `zpmod` is an optional measured variant and diagnostic integration. A project baseline measures its ordinary execution path. Source-study output must be functional, precise and explicit about overlapping inclusive durations before automation consumes it. Automatic compilation benefits are evaluated with plain-source, first-run, warmed and manual-bytecode controls.
6. Roll out through the annex, small-plugin and standalone-tool pilots in #673. Workflow and analyzer revisions are independently pinned; changes to either require consumer evidence. Restore prior reviewed pins for rollback. Workflow-release expansion follows #543.

## Consequences

The organization shares integration code without creating a second rule engine or a universal workload runner. Repository-specific coverage and compatibility remain visible responsibilities. Parser gaps can delay a repository's enrollment without blocking unrelated consumers. Benchmark interpretation retains the instrumentation mode and runner noise context.

This decision does not declare the initiative complete, promote observation to enforcement, or claim that every consumer is covered. The native-oracle rollout and dependent enforcement are deferred by the maintainer; implementation and reporting work can proceed independently.

## Alternatives considered

- Require one current analyzer across every repository immediately: rejected because coverage and compatibility differ.
- Use zpmod as the universal benchmark runner: rejected because compilation changes execution and sourced-file timings do not cover all project operations.
- Keep duplicated workflows and report formats: rejected because drift increases maintenance and makes failures harder to compare.

## References

- [ADR-0009](0009-testing-ci-strategy.md): class-specific quality checks.
- [ADR-0024](0024-benchmarks-observed-not-gated.md): benchmark methodology and report contract.
- [ADR-0030](0030-zsh-lint-parser-fork-trigger-fired.md): staged parser migration.
- [Shared lint runbook](../runbooks/zsh-lint-ci.md): integration inputs, evidence and rollback.
- [Issue #543](https://github.com/z-shell/.github/issues/543): workflow-specific release pilot.
