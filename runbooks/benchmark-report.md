# Shared benchmark report validation

`actions/benchmark-report` validates and presents a completed ADR-0024 comparison in the workload's existing job. It never executes a benchmark or installs zpmod. Repositories retain their own fixtures, correctness assertions, baseline selection and balanced sampling. Timing flags request review; malformed evidence and functional failures fail validation.

## Calling the action

Use Linux with Python 3.10 or newer and Bash. Give the job only `contents: read`, retain caller-owned concurrency and a timeout, and pass no secrets. Pin the action to a reviewed full commit SHA before consumer enrollment. Run it after the producer, including after a producer failure when diagnostic artifacts are needed. Do not set `continue-on-error` on production validation.

Inputs are literal repository-relative regular files; absolute paths, parent traversal, Git metadata and symlinks are rejected. Reports are limited to 16 MiB. The required `report` input names the comparison JSON. Optional `control-report` supplies the raw second baseline report when the comparison lacks `control_identity`, as in Zi's existing producer. Give `artifact-name` a unique value per invocation; it defaults to `benchmark-evidence`.

For local verification:

```sh
python3 scripts/benchmark_report.py --root /checkouts/project \
  --report benchmark-comparison.json --control-report results/control.json \
  --output /scratch/benchmark-validation
```

For the annex, whose comparison includes `control_identity`, omit `--control-report`. The action runs this same validator from its pinned action source and exposes `evidence-directory` for later local steps. It uploads raw input reports, `validation.json` and `summary.md` for 14 days, including rejected evidence when the files were readable. It appends the summary to the job and emits notices for candidate and A/A flags, without comments, repository writes or an elevated token.

## What acceptance means

The validator checks schema version 1, nonempty case coverage, known source identities, matching Zsh/architecture/CPU/runner-image identities and equal positive warmup/sample counts. It derives comparability independently of the producer's boolean. Baseline and candidate revisions may differ. The A/A control must have the baseline's source identity, environment and counts, the same case inventory, and identical first-baseline measurements. A supplied raw control report must also match the comparison's second-baseline samples.

Every raw duration must be finite and nonnegative. Count, minimum, median and nearest-rank p95 are checked against samples. Zi serializes medians to three decimal places, so the validator permits 0.000500001 ms absolute tolerance for median rounding. Other statistics and deltas use 1e-9 absolute tolerance; every numeric comparison also uses 1e-9 relative tolerance. Median and p95 changes are recalculated from the serialized statistics. Percentages must be null when the baseline is zero.

Flags must match the reported thresholds. The defaults are greater than 10% median or greater than 15% p95; a producer may tighten these values but cannot loosen them. A flag never causes a failure. A/A flags are shown separately as noise evidence. A functional-failure row on either side or in the control fails validation. Missing control provenance, incomplete producer reports, unsupported-case extensions and incompatible identities are rejected rather than presented as complete comparisons. Zi callers should choose a fully supported case set when they require accepted comparison evidence.

This is consistency validation, not attestation that a producer used the declared source, ran network-free or measured on one runner. The workload workflow must establish those properties. The validator does not compare unrelated historical reports, impose timing gates or qualify a release. Reports may retain additional producer metadata, but unknown metadata cannot replace required evidence. Keep private paths and environment values out of producer reports before uploading them.

## Verification and upgrades

Run `python3 -m unittest scripts/test_benchmark_report.py -v`. `Benchmark Report Tests` exercises both a nonfatal slowdown and a rejected incompatible report through the real action, with artifacts retained for both. Consumer adoption should use positive, negative and noise-control evidence before changing a pin. Roll back by restoring the previously reviewed action pin; never waive invalid evidence to obtain a passing job.

Current producer references are [Zi's comparison](https://github.com/z-shell/zi/blob/8448b4a2323099b3034db9b40b598eef702ae9b2/benchmarks/compare.zsh) and [the annex's runner](https://github.com/z-shell/z-a-meta-plugins/blob/f3f95b9ec33978b18813ed6b02285cc58548c339/benchmarks/run.py). Zi's comparison alone omits the control identity and does not compare runner-image/CPU fields; the raw control report and this validator close those evidence gaps without editing its workload runner.

See [ADR-0024](../decisions/0024-benchmarks-observed-not-gated.md) for the schema and publication policy. Adoption and remaining qualifications are tracked in [#673](https://github.com/z-shell/.github/issues/673) and [#675](https://github.com/z-shell/.github/issues/675).
