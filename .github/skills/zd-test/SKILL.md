---
name: zd-test
description: Reproduce Linux Zsh failures, validate module ABI boundaries, or collect controlled benchmark evidence with zd. Use when container isolation or an explicit runtime matters, rather than for routine syntax-only checks.
---

# Controlled Zsh execution

Read the owning repository's checks and compatibility floor, then the organization
[selection guidance](../../instructions/zd-validation.instructions.md). Keep the
user's workload and target versions.

Choose `runtime` for source tests or `module-build` for a compiled module. Obtain
an already qualified immutable image and the corresponding pinned zd runner.
Inspect the runner's `--help` and
[controlled-execution contract](https://github.com/z-shell/zd/blob/main/docs/controlled-execution.md)
when preparing a run. Do not infer installed tools from a legacy zd tag.

Run the repository-owned entrypoint with a fresh output directory outside its Git
source tree. Pass prepared Git fixtures as named inputs. Finish installation,
cloning and image preparation before a benchmark; leave workload network access
disabled. Declare required non-secret environment values explicitly. Preserve
command argument boundaries instead of evaluating a command string.

Inspect `execution.json`, runtime/package identities, workload logs and raw
reports. A container's zero exit status is useful only alongside the repository's
observable assertions. Exercise expected failure and timeout propagation when
introducing a new entrypoint or image. For performance, inspect same-run A/A noise
before attributing a delta to source changes; use the existing `benchmark-report`
action for ADR-0024 comparisons.

Report passed, failed and unavailable coverage separately. Retain evidence and
state whether native platforms, real startup fixtures or interactive behavior
remain unmeasured. The
[integration runbook](../../../runbooks/zd-validation.md) owns CI setup and pilot
entrypoints. This skill grants no publication or external-write authority.
