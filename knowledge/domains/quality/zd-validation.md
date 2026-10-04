# Controlled zd validation

zd owns the execution environment; repositories own their test commands and benchmark workloads. The organization action transports those commands and retains evidence. It does not install a plugin manager or choose a workload. Use the [selection guidance](../../../.github/instructions/quality/controlled-validation.instructions.md) to decide when a container helps.

## Prepare and qualify the environment

Use zd's [controlled execution guide](https://github.com/z-shell/zd/blob/f8d74a1c916d42c99fea2600adff3607f67ee4bc/docs/controlled-execution.md). It defines `runtime` and `module-build`, release archive checksums, explicit runtime patches, image qualification and CLI behavior. Legacy zd images do not claim this profile contract. Build/pull a qualified image before execution. Record its immutable registry digest, actual Zsh release, patch identity, architecture and package manifest. Benchmark images must match the Docker host architecture; emulation is correctness evidence only.

Clone or prepare fixed dependency revisions outside the timed workload. Pass public Git fixture roots as named inputs, such as `zi`. zd snapshots Git-selected files into disposable writable state without Git metadata or ignored build caches, records original revisions and content hashes, and rejects input changes during execution. The source and fixture mounts are read-only. Commands receive a clean HOME, ZDOTDIR and explicit environment. Keep secrets out of arguments, fixtures and artifacts.

Locally, invoke `python3 /path/to/zd/bin/zd run` with an immutable image, `--profile`, `--source`, fresh `--output` outside the checkout, optional `--input` and the repository command after `--`. Benchmark mode forbids workload network access. CPU affinity is optional and does not reserve a CPU or control host load.

## Integrate the composite action

`actions/run-zd` requires Linux, Docker and Python 3.10+. Pin the organization action to a reviewed full commit and supply a reviewed full `zd-ref` that contains `scripts/zd.py`. The action downloads that exact runner into temporary storage; it never falls back to a branch or tag. `image` is an immutable registry digest; `pull: false` also permits an already-loaded local image ID for qualification. Dependencies are prepared before the action. Its workload network is disabled.

`command` is a JSON array, for example `["zsh", "-f", "scripts/zd-check.zsh"]`. `fixtures` is a JSON object of names to prepared Git checkout roots. Arguments remain separate and are never evaluated as a shell command. `profile`, `mode`, `timeout` and optional `cpuset` are explicit. Outputs live under `evidence-directory/execution`; the entire directory is uploaded even after a functional failure or timeout. Preparation failures have separate evidence and are unavailable validation, rather than a source verdict.

For an ADR-0024 producer, invoke `actions/benchmark-report` afterward with `root` equal to the run-zd `evidence-directory` output and `report` relative to that directory, for example `execution/comparison/comparison.json`. This root input preserves the default workspace-root behavior for existing callers. Keep report validation after a failed workload if diagnostic evidence is needed; an absent or incomplete comparison must fail validation. Both actions require only `contents: read`; neither comments on pull requests or publishes an image.

Pilot workflows pin already published organization and zd commits in source, check out that exact organization revision and use its local action path. Dispatch selects only a qualified immutable image digest; it cannot select executable shared revisions. A full-SHA format check alone does not establish that dispatched code is trusted. Draft prerequisite pins still need review of record before the pilot is used. Do not invent a pin for an uncommitted implementation. After prerequisite review and hosted qualification, use a reviewed immutable action reference before enabling automatic PR runs. Image publication is a separate release operation.

## Repository pilots

- `zpmod/scripts/zd-check.zsh` uses `module-build`, builds vendored headers and
  the staged module, explicitly selects the image's Zsh for CTest and optionally
  runs `benchmarks/compare.py`. The comparison wraps its existing four-mode
  synthetic workload. Default baseline/candidate/control are the same module;
  that qualifies collection, not a performance improvement. A separate baseline
  needs a prepared module for the same ABI and its source revision.
- `z-a-meta-plugins/scripts/zd-check.py` uses `runtime`, runs the existing source
  suite, syntax/report tests and, with `--benchmark` plus named Zi input, the
  existing sensitivity/failure tests followed by its full loader fixture.
  Other plugin groups and interactive latency remain outside this pilot.

Read each repository's benchmark guide for counts, warmup scope and timer boundaries. Do not compare native reports with container reports. A/A noise requires investigation or a quieter-host rerun before attributing source deltas. Functional failure invalidates timings; ADR-0024 percentage flags never fail on performance alone. Retain runtime identity, execution status, test assertions, raw samples and reports together. Preserve native platform/terminal coverage.

## Verify an integration

Qualify an image with a successful observable assertion, a known failing command and a bounded timeout, including absence of the exact owned container afterward. Run the repository suite and the existing report validator. For a new benchmark producer, prove a deliberate slowdown is flagged without failing on timing, incompatible identities are rejected and a functional failure cannot produce an accepted comparison. Report passed, failed and unavailable checks separately.

Local qualification does not establish hosted Actions success or automatic skill delivery. Mandatory selection guidance is routed through the public manifest; `zd-test` is optional. Verify runtime discovery after normal reviewed delivery under ADR-0014/0032, without relying on the skill for policy.
