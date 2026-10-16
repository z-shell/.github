---
applyTo: ".github/workflows/*.yml,.github/workflows/*.yaml"
description: "Canonical Z-Shell CI/CD workflow conventions, security hardening, action pinning, naming rules, and permission baselines"
---

# GitHub Actions CI/CD Conventions

Canonical guidelines for authoring, reviewing, and hardening GitHub Actions workflows across Z-Shell repositories.

---

## 1. Naming & Structure Conventions (ADR-0005)

- **File Naming**: Use `kebab-case.yml`. Group related workflows by prefix (e.g., `ci-*`, `docker-*`, `release-*`, `lint-*`).
- **Workflow `name:`**: Plain text only, Title Case, maximum 50 characters. **No emojis** in workflow names.
- **Job IDs**: Use `kebab-case`.
- **Job `name:`**: Plain text only, Title Case. **No emojis** in job names.
- **Step `name:`**: Sentence case or Title Case with imperative verbs. Emojis are permitted only within step names as visual scanning landmarks in logs.

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
```

---

## 2. Security Hardening & Supply-Chain Integrity

### Action Pinning

- **Organization reusable workflows**: Reference reusable workflows from `z-shell/.github/.github/workflows/` at `@main` ([ADR-0042](../../../decisions/0042-organization-reusable-workflows-at-main.md)). A change merged to the protected `main` of `z-shell/.github` then reaches every caller without a pull request in each repository. This covers only those reusable workflows; organization actions under `z-shell/.github/actions/` are pinned like any other action.
- **Immutable Commit SHAs**: Every other remote action and reusable workflow `uses:` reference MUST be pinned to a full 40-character commit SHA.
- **Version Comments**: Append the associated release version after the SHA for auditability (e.g., `# v4.3.1`).
- **Existing SHA pins**: A caller that pins an organization reusable workflow to a full SHA with the earlier interim `# main` comment remains valid until it moves to `@main` in its own reviewed change. Such a pin must name a commit on the default branch of `z-shell/.github`, never a pull request's branch commit. A squash merge leaves that commit on no branch, and callers pinned to it end every run in a startup failure with no jobs ([#774](https://github.com/z-shell/.github/issues/774)). Before pinning, `gh api repos/z-shell/.github/compare/main...SHA --jq .status` must print `behind` or `identical`. The daily Community Health Audit reports any other pin (`repo-settings-audit.rb --workflow-pins`).
- **Prohibited**: Never use mutable tags or branches (e.g., `@v4`, `@main`, `@latest`) for anything other than organization reusable workflows.

```yaml
# Correct
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1

# Forbidden
- uses: actions/checkout@v4
```

### pinact exception for organization reusable workflows

pinact 4.1.1 would pin an `@main` reference, and it rejects the `# main` comment on an existing SHA pin because it requires a version comment. Reuse [the shared pinact template](../../../templates/pinact/.pinact.yaml), observed in [zunit#27](https://github.com/z-shell/zunit/pull/27) and [zpmod#114](https://github.com/z-shell/zpmod/pull/114). Copy it to the caller repository's `.pinact.yaml` only when no pinact configuration exists. Otherwise merge its `ignore_actions` entries into the existing configuration, preserving its settings and avoiding a second competing config file. The template retains configuration version 3; it does not install or enable pinact.

The exception matches only `z-shell/.github/.github/workflows/` references whose ref is exactly `main` or a full lowercase 40-hex SHA; pinact matches both patterns against the whole name and ref. Other organization actions and third-party actions remain subject to pinact's checks. pinact skips all validation and updates for matching entries: for a SHA pin the regex restricts the ref's shape but does not verify the commit exists, belongs to the repository, or has been reviewed. Do not broaden the exception to other repositories, actions or refs. See [pinact 4.1.1 configuration](https://github.com/suzuki-shunsuke/pinact/blob/v4.1.1/docs/config.md#ignore_actions) for exception semantics.

### Permissions (Least Privilege)

- **Top-Level Baseline**: Declare `permissions: { contents: read }` (or stricter `permissions: {}`) at the root workflow level.
- **Job-Level Overrides**: Elevate permissions only on the specific jobs that require them (e.g., `packages: write`, `id-token: write`).

### Secrets & Authentication

- Pass secrets strictly through environment variables (`env:`); never inline secrets into `run:` scripts.
- Use OpenID Connect (OIDC) for cloud integrations instead of long-lived credentials (`id-token: write`).

---

## 3. Concurrency & Execution Control

- **Branch / PR Workflows**: Declare a `concurrency` block with `cancel-in-progress: true` to prevent resource waste and race conditions on rapid pushes.
- **Required checks with overlapping events**: When push and PR metadata events can produce checks for the same head, do not cancel or supersede those short runs. GitHub retains cancelled check results; even `cancel-in-progress: false` can replace a pending run. Omit concurrency for this documented case (z-shell/zi#597), and verify the effective required checks. A reusable workflow that owns concurrency must use a group distinct from its caller, or the caller must omit its own group.
- **Release / Deployment Workflows**: Set `cancel-in-progress: false` to ensure in-flight deployments complete deterministically.

---

## 4. Reusable Workflows (`workflow_call`)

- Explicitly declare `type` and `required` for every input in `workflow_call`.
- Declare `default` only for optional inputs. A `required: true` input must not carry one, because the caller always supplies the value and the default is unreachable.
- When a workflow is **also** triggered directly (`push`, `pull_request`, `schedule`), put the operative fallback in the job step, for example `: "${VAR:=...}"`. The `inputs` context holds "the inputs of a reusable or manually triggered workflow", so on a direct trigger it is empty and `workflow_call` defaults are never applied. A default declared on the input is then dead text on the path the workflow actually takes, and an empty pattern reaching `grep -E` matches every line.
- Reference organization reusable workflows at `@main` and any other called workflow at a pinned immutable ref.
- Expose job `outputs` cleanly for downstream dependent jobs (`needs:`).

The shared `zsh-ci.yml` owns native syntax and optional compilation. Callers
declare extensionless Zsh sources through newline-delimited `extra-files`,
set `require-sources: true` when an empty inventory is an error, and enable
`run-zcompile` for the organization baseline. Existing `*.zsh` discovery is
retained. Compilation uses disposable output outside the checkout. Consumers
own source classification, supported versions and functional tests.

The shared `codeql.yml` supports `workflow_call` for Actions
analysis; it does not analyze Zsh semantics. Both native Zsh and CodeQL accept
`checkout-ref` for an exact candidate SHA and use distinct concurrency groups
when called from the same parent workflow. Preserve required-check names and
prove caller coverage before changing repository rulesets.

---

## 5. Organization-Retired Patterns

The following patterns are retired by Z-Shell policy. This is an organization
decision, not a claim that each upstream project is deprecated. Do not introduce
new uses; migrate existing uses through their owning rollout and runbook.

- `actions/labeler` (label management is handled centrally via `runbooks/labels.md`)
- `sync-labels.yml`, `pr-labels.yml`
- `assign.yml` and any per-repository `actions/add-to-project` workflow (Project 28 membership is reconciled centrally; see `runbooks/project-tracker.md`)
- `stale.yml`, `lock.yml`, `rebase.yml`
- Unpinned or tag-referenced third-party actions

---

## 6. Pre-Merge Verification Checklist

- [ ] Filename is `kebab-case.yml` with appropriate category prefix.
- [ ] Workflow `name:` and Job `name:` contain NO emojis.
- [ ] Top-level `permissions:` is declared with minimum necessary scope.
- [ ] Concurrency follows the execution-control rules above, including documented required-check exceptions and distinct caller/callee groups.
- [ ] Organization reusable workflows from `z-shell/.github/.github/workflows/` are referenced at `@main` (or keep an existing full-SHA pin on the default branch); every other remote action and reusable workflow is pinned to a 40-character commit SHA with its release comment.
- [ ] Any pinact exception uses the shared template's exact repository/workflow and its `main` or full-SHA ref match.
- [ ] Actionlint and YAML syntax checks pass.
