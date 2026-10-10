# Shared Zsh lint integration

`.github/workflows/zsh-lint.yml` runs a pinned analyzer against reviewed Zsh source roots. Consumers own those roots and their `zsh-lint.json`; the analyzer owns rules and configuration semantics. Native syntax, compilation, compatibility and functional tests remain separate checks.

## Inputs

| Input          | Contract                                                                                                                                                                                                            |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `paths`        | Required newline-delimited repository-relative files or dedicated Zsh directories. Directories include every regular file recursively, including hidden and extensionless files. Paths are deduplicated and sorted. |
| `zsh-lint-ref` | Required lowercase 40-character analyzer commit SHA. Use a reviewed published release.                                                                                                                              |
| `config`       | Optional explicit repository-relative configuration file. Empty preserves the analyzer's configuration discovery for existing callers. Enrolled projects should supply their reviewed configuration explicitly.     |
| `mode`         | `strict` by default. `observe` tolerates semantic findings only; parser errors, invalid configuration, incomplete reports, timeout and tool failures still fail.                                                    |

Inputs are literal paths, not shell expressions or globs. A directory is a reviewed declaration that all its files are Zsh; the workflow does not infer dialect. Do not pass the repository root or a mixed-language directory. Symlinks, parent traversal, absolute paths, Git metadata, missing paths and empty selections are rejected. Intentional invalid-language fixtures belong outside production roots.

The optional `artifact-name` input defaults to `zsh-lint-report`. Give each invocation a unique name if a workflow calls lint more than once. Result metadata records the analyzer and workflow revisions.

Source-root and symlink validation is stricter than the original wrapper. Publish this contract as a new major workflow release; existing immutable caller pins retain the old behavior until deliberately migrated.

## Calling and upgrading

Call the reusable workflow as a job with `contents: read`. The caller owns concurrency. Pin the workflow and analyzer independently to full SHAs with release comments. The workflow checks out its helper at its own resolved workflow revision, never from the caller's source. Go setup reads the pinned analyzer's `go.mod`.

Keep the complete selected project in each run so cross-file rules see unchanged sources. A required check must report for every applicable pull request; avoid workflow-level path filters that leave its status pending. Before requiring lint, verify parser compatibility, the selected inventory, the repository compatibility floor, and both passing and deliberately failing changes. Observation runs remain visibly marked and are not a substitute for enforcement.

For upgrades, compare diagnostics at fixed consumer revisions, explain additions and removals, and exercise the three pilot source profiles. Workflow-specific release expansion follows issue #543. Roll back by restoring the previous reviewed workflow and analyzer pins. Do not suppress parser failures or remove native checks to accommodate a tooling regression.

## Evidence and failure behavior

The artifact contains `inventory.json`, the unmodified analyzer `diagnostics.json`, `stderr.txt`, integration `result.json`, and `summary.md` when those stages were reached. The integration validates diagnostic envelope version 1, counts, file identities and exit status before interpreting findings. Configuration failures written to stderr cannot become a successful observation result. Build/setup failures may occur before an artifact exists and remain failed jobs.

Annotations escape workflow-command metacharacters; summaries avoid interpreting analyzer text as Markdown. Artifacts retain detailed diagnostics for 14 days. The analyzer gets five minutes and the job gets fifteen minutes. Timing out is an execution failure, not clean lint.

## Verification

Run `python3 -m unittest automation/ci/test_zsh_lint_ci.py -v`. `Zsh Lint Tests` also calls the real reusable workflow with the pinned v1.4.0 analyzer, exercising workflow-source resolution, toolchain selection, JSON interpretation and artifact upload. Consumer qualification remains a separate rollout step under initiative #673.
