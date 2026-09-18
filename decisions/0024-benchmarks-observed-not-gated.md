# 24. Benchmarks Are Observed, Not Gated, With Flag Thresholds and Committed Per-Release Results

- **Status:** ACCEPTED
- **Date:** 2026-09-18
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

Two repositories ship benchmarks with different shapes. `z-shell/zpmod` runs a Zsh harness that emits JSON, TSV, SVG, and Markdown, commits per-release results under `benchmarks/results/<tag>-<os>-<arch>/` (today `v2.0.6-linux-x86_64`), and states that hosted-runner results are evidence, not a blocking gate. `z-shell/z-a-meta-plugins` drives a baseline-versus-candidate comparison from Python on every pull request: alternating order, five warmups, thirty samples, median and p95, a functional failure invalidating the timings, and no timing thresholds. `z-shell/zi` is adding a third suite ([z-shell/zi#553](https://github.com/z-shell/zi/issues/553)) after a promotion review found a +20% ice-tokenizing regression only through an ad hoc A/B ([z-shell/zi#554](https://github.com/z-shell/zi/issues/554)).

Nothing in `decisions/`, `PATTERNS.md`, or the runbooks records how benchmark results relate to merging, which statistics a comparison must report, or where results are published. [ADR-0009](0009-testing-ci-strategy.md) settles the analogous question for coverage ("observed, not gated") but is silent on performance. Each repository has therefore decided alone, and the third suite would have been a third convention.

## Decision

1. **Observed, not gated.** A benchmark job never fails on timing. It reports, and the maintainer decides. This extends ADR-0009's coverage rule to performance and matches zpmod's stated stance on hosted runners.
2. **Flag thresholds for review.** A comparison marks a case for review when its median regresses by more than 10 percent or its p95 by more than 15 percent against the baseline measured in the same run. A flag is a notice on the job and the pull request, not a failure. Repositories may tighten the thresholds, not loosen them, and must record the values in their benchmark README.
3. **Comparison shape.** A comparison measures baseline and candidate in the same runner with alternating (balanced) order, discards warmup rounds, reports median, p95, minimum, and sample count per variant and the median and p95 deltas, and includes an A/A control (the baseline measured twice) so the noise floor is visible next to the real comparison. A functional failure on either side invalidates that case and fails the job, because timing a broken behaviour is meaningless.
4. **Determinism.** Benchmark workloads are network-free and fixture-driven. Network-dependent behaviour belongs in smoke or integration jobs, not in a comparison.
5. **Publication.** Per-release results are committed by a maintainer under `benchmarks/results/<tag>-<os>-<arch>/`, the naming zpmod already uses, after a release, together with the exact source revision, Zsh version, architecture, and runner or host identity. Automation uploads artifacts and job summaries; it never commits results. Results are compared only when those identity fields match.
6. **Canonical comparison schema, version 1.** A comparison report carries `schema_version: 1`, `baseline` and `candidate` identity (`label`, `source_revision`, `environment{zsh_version,architecture,cpu,runner_image}`, `workload{warmups,samples}`), a boolean `comparable` derived from those fields, and `cases[case]` where each case is either `{failure: {baseline, candidate}}` or `{results: {baseline, candidate}, change, flag}` with `results[variant] = {median, p95, min, count, samples}` and `change = {median_delta_ms, median_delta_percent, p95_delta_ms, p95_delta_percent}`; `flagged` and `failed` list the affected case names. `z-shell/zi` implements this schema. `z-a-meta-plugins` today emits `results[variant][metric]{median,p95,samples}` and `change[metric]{median_delta_ms,median_delta_percent}` per metric; it adapts to version 1 (adding `min`, `count`, and the p95 deltas, and lifting its per-metric nesting to one case per metric or an explicit `metrics` map in a schema revision) before the shape is admitted to `PATTERNS.md` as an observed two-repository pattern. Until then the pattern is proposed, not observed.

## Consequences

### Positive

- A performance regression becomes visible in the pull request that introduces it, with its size, without blocking unrelated work on hosted-runner noise.
- Three repositories share one vocabulary, so a reader can compare reports and reviewers know what a flag means.
- Committed per-release results give every release a performance record tied to an exact revision.

### Costs and risks

- A flag that nobody reads is a regression that ships. The weekly organization review ([`runbooks/org-review.md`](../runbooks/org-review.md)) lists flagged benchmark runs under "Needs review".
- Hosted runners are noisy; the A/A control makes that visible but does not remove it. Repeated flags on the control column mean the runner, not the change.
- The thresholds are chosen from the first zi A/B, where unrelated cases sat within ±1 percent and the real regression was +20 percent; they should be revisited after the first ten flagged runs.

## Alternatives considered

1. **Blocking above a threshold.** Rejected for now: without an A/A history, hosted-runner noise produces false reds and forces a bypass path, which ADR-0013 discourages. Revisit once the control column has a track record.
2. **Report only, no thresholds.** Rejected: z-a-meta-plugins' experience is that unhighlighted tables are not read; the zi regression was found only because a human ran and read an A/B.
3. **One central benchmark runner for the organization.** Deferred: zpmod measures a compiled module and z-a-meta-plugins measures real plugin groups; the workloads differ too much for one runner, while the report shape can be shared.

## References

- [z-shell/.github#629](https://github.com/z-shell/.github/issues/629): the decision request.
- [z-shell/zi#553](https://github.com/z-shell/zi/issues/553), [z-shell/zi#554](https://github.com/z-shell/zi/issues/554), [z-shell/zi#555](https://github.com/z-shell/zi/issues/555): the zi suite and the two regressions it exists to track.
- `z-shell/zpmod` `benchmarks/README.md` and `z-shell/z-a-meta-plugins` `benchmarks/README.md`: the two existing conventions.
- [ADR-0009](0009-testing-ci-strategy.md): coverage observed, not gated.
