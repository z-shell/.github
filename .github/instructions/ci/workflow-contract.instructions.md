---
applyTo: ".github/workflows/*.yml,.github/workflows/*.yaml"
description: "Canonical Z-Shell CI/CD workflow conventions, security hardening, action pinning, naming rules, and permission baselines"
---

<!-- GENERATED from knowledge/domains/ci/workflow-contract.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

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

- **Immutable Commit SHAs**: Every remote action and reusable workflow `uses:` reference, including organization references, MUST be pinned to a full 40-character commit SHA.
- **Version Comments**: Append the associated release version after the SHA for auditability (e.g., `# v4.3.1`). For organization reusable workflows from `z-shell/.github/.github/workflows/` without an adopted workflow release, retain the established interim `# main` comment. The comment identifies the source branch; the full SHA selects the code.
- **Prohibited**: Never use mutable tags (e.g., `@v4`, `@main`, `@latest`).

```yaml
# Correct
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1

# Forbidden
- uses: actions/checkout@v4
```

### Interim pinact exception for organization reusable workflows

pinact 4.1.1 rejects the interim `# main` comment on a SHA pin because it requires a version comment. Reuse [the shared pinact template](../../../templates/pinact/.pinact.yaml), observed in [zunit#27](https://github.com/z-shell/zunit/pull/27) and [zpmod#114](https://github.com/z-shell/zpmod/pull/114). Copy it to the caller repository's `.pinact.yaml` only when no pinact configuration exists. Otherwise merge the `ignore_actions` entry into the existing configuration, preserving its settings and avoiding a second competing config file. The template retains configuration version 3; it does not install or enable pinact.

The exception matches only `z-shell/.github/.github/workflows/` references with a full lowercase 40-hex SHA. Mutable refs, other organization actions and third-party actions remain subject to pinact's checks. pinact skips all validation and updates for matching entries, not just the comment check: the regex restricts the ref's shape but does not verify the commit exists, belongs to the repository, or has been reviewed. Continue to verify the selected workflow and commit through the repository's checks and PR review. Do not broaden the exception or use a branch or tag as the actual ref.

This is an interim compatibility measure for [#663](https://github.com/z-shell/.github/issues/663). Once [#543](https://github.com/z-shell/.github/issues/543) establishes the applicable immutable workflow releases and a caller adopts them, use the associated workflow release comment and remove its unused exception. Downstream adoption and release changes require their own reviewed rollout. See [pinact 4.1.1 configuration](https://github.com/suzuki-shunsuke/pinact/blob/v4.1.1/docs/config.md#ignore_actions) for exception semantics.

### Permissions (Least Privilege)

- **Top-Level Baseline**: Declare `permissions: { contents: read }` (or stricter `permissions: {}`) at the root workflow level.
- **Job-Level Overrides**: Elevate permissions only on the specific jobs that require them (e.g., `packages: write`, `id-token: write`).

### Secrets & Authentication

- Pass secrets strictly through environment variables (`env:`); never inline secrets into `run:` scripts.
- Use OpenID Connect (OIDC) for cloud integrations instead of long-lived credentials (`id-token: write`).

---

## 3. Concurrency & Execution Control

- **Branch / PR Workflows**: Declare a `concurrency` block with `cancel-in-progress: true` to prevent resource waste and race conditions on rapid pushes.
- **Release / Deployment Workflows**: Set `cancel-in-progress: false` to ensure in-flight deployments complete deterministically.

---

## 4. Reusable Workflows (`workflow_call`)

- Explicitly declare `type` and `required` for every input in `workflow_call`.
- Declare `default` only for optional inputs. A `required: true` input must not carry one, because the caller always supplies the value and the default is unreachable.
- When a workflow is **also** triggered directly (`push`, `pull_request`, `schedule`), put the operative fallback in the job step, for example `: "${VAR:=...}"`. The `inputs` context holds "the inputs of a reusable or manually triggered workflow", so on a direct trigger it is empty and `workflow_call` defaults are never applied. A default declared on the input is then dead text on the path the workflow actually takes, and an empty pattern reaching `grep -E` matches every line.
- Reference called workflows using pinned immutable refs.
- Expose job `outputs` cleanly for downstream dependent jobs (`needs:`).

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
- [ ] `concurrency:` block is present with `cancel-in-progress` set appropriately.
- [ ] All remote actions and reusable workflows are pinned to 40-character commit SHAs with associated release comments, or the documented interim `# main` comment for organization reusable workflows.
- [ ] Any interim pinact exception uses the shared template's exact repository/workflow and full-SHA match; the selected workflow and commit are verified separately.
- [ ] Actionlint and YAML syntax checks pass.
