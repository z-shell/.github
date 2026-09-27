---
description: "Select controlled zd environments for reproducible Linux validation and benchmarks"
applyTo: "**"
---

# Controlled zd validation

Consider zd for container-sensitive failures, repeatable Linux benchmarks and explicit Zsh runtime or module ABI validation. Use the repository's existing native commands when they already answer a small syntax or documentation check. Keep native macOS, terminal and interactive checks where those behaviors matter. A Linux container does not establish that platform coverage.

Choose zd's `runtime` profile for source/plugin checks and `module-build` for compiled modules. Select the repository compatibility floor and relevant supported boundaries. Pin the execution tool to a full commit and the image to a digest; record the actual Zsh version, architecture and any explicit runtime patch. A patched runtime is separate evidence from its stock release. Qualify the image before relying on it; do not silently substitute versions or patches.

Prepare dependencies and fixture checkouts before execution. Use zd's named inputs, clean home and default network-disabled workload. Repository entrypoints own tests, benchmark cases and output formats. Do not add zpmod, a package manager or a new fixture workload merely because the image can run it.

Benchmarks follow ADR-0024: same-run baseline/candidate plus A/A noise evidence, balanced order, warmups and raw samples. Functional failure invalidates timing; percentage flags request review without failing on timing alone. Keep container and native results separate. CPU affinity does not reserve the host CPU or clear filesystem caches.

Use [the runbook](../../runbooks/zd-validation.md) for local/CI integration and the optional `zd-test` skill for execution procedure. Existing publication and repository authorization boundaries still apply.
