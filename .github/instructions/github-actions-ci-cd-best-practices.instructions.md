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

- **Immutable Commit SHAs**: Every external action `uses:` reference MUST be pinned to a full 40-character commit SHA.
- **Version Comments**: Append a human-readable version comment after the SHA for auditability.
- **Prohibited**: Never use mutable tags (e.g., `@v4`, `@main`, `@latest`).

```yaml
# Correct
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1

# Forbidden
- uses: actions/checkout@v4
```

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

- Explicitly declare `type`, `required`, and `default` for every input in `workflow_call`.
- Reference called workflows using pinned immutable refs.
- Expose job `outputs` cleanly for downstream dependent jobs (`needs:`).

---

## 5. Organization-Retired Patterns

The following patterns are retired by Z-Shell policy. This is an organization
decision, not a claim that each upstream project is deprecated. Do not introduce
new uses; migrate existing uses through their owning rollout and runbook.

- `actions/labeler` (label management is handled centrally via `runbooks/labels.md`)
- `sync-labels.yml`, `pr-labels.yml`
- `stale.yml`, `lock.yml`, `rebase.yml`
- Unpinned or tag-referenced third-party actions

---

## 6. Pre-Merge Verification Checklist

- [ ] Filename is `kebab-case.yml` with appropriate category prefix.
- [ ] Workflow `name:` and Job `name:` contain NO emojis.
- [ ] Top-level `permissions:` is declared with minimum necessary scope.
- [ ] `concurrency:` block is present with `cancel-in-progress` set appropriately.
- [ ] All external actions are pinned to 40-character commit SHAs with `# vX.Y.Z` comments.
- [ ] Actionlint and YAML syntax checks pass.
