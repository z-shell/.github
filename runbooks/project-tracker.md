# Runbook — Project tracker

Use this runbook for the organization-wide Z-Shell Tracker.

## Tracker identity

- Project: `z-shell — Org-wide`
- URL: `https://github.com/orgs/z-shell/projects/28`
- Owner: `z-shell`
- Project number: `28`
- Auto-add label: `meta:org-tracked`

## What belongs on the tracker

Track issues that need cross-repository or maintainer-level attention:

- cross-repository work
- release blockers
- security-sensitive work
- strategic or roadmap work
- organization infrastructure work

Do not add ordinary single-repository bugs, support questions, or small cleanup tasks just because they are actionable.

## Auto-add paths

There are two supported auto-add paths.

### Preferred: Project v2 built-in workflow

In the GitHub Project UI, enable the Project workflow that auto-adds issues with this filter:

```text
is:issue label:meta:org-tracked
```

GitHub's public GraphQL API currently exposes Project v2 workflow names and enabled state, but not the auto-add filter configuration. Verify the filter in the Project UI when auditing this setup.

### Repository workflow fallback

This repository provides `.github/workflows/project-tracker.yml`.

It:

- runs directly for issues in `z-shell/.github`
- can be reused by other repositories through the Project Tracker workflow template
- adds issues labelled `meta:org-tracked` to Project 28 with `gh project item-add`

For organization-wide reliability, configure an organization or repository secret named `Z_SHELL_PROJECT_TOKEN` with permission to write to the organization Project v2 board. The workflow falls back to `github.token`, but that token may not have organization-project write access in every repository.

## Installing in another repository

Use the Project Tracker starter workflow from **Actions > New workflow**, or add this caller workflow:

```yaml
---
name: Project Tracker

on:
  issues:
    types: [opened, labeled, reopened]

permissions:
  contents: read
  issues: read

concurrency:
  group: ${{ github.workflow }}-${{ github.event.issue.node_id }}
  cancel-in-progress: true

jobs:
  add-tracked-issue:
    if: contains(github.event.issue.labels.*.name, 'meta:org-tracked')
    uses: z-shell/.github/.github/workflows/project-tracker.yml@main
    with:
      issue_url: ${{ github.event.issue.html_url }}
    secrets: inherit
```

## Verification

To verify auto-add behavior:

1. Create or choose a test issue in the repository.
2. Apply `meta:org-tracked`.
3. Wait for either the Project built-in workflow or the repository workflow to run.
4. Confirm the issue appears on Project 28:

```sh
gh issue view <issue-number> --repo z-shell/<repo> --json projectItems
```

If the issue does not appear, add it manually and investigate the project workflow or token:

```sh
gh project item-add 28 --owner z-shell --url https://github.com/z-shell/<repo>/issues/<issue-number>
```

## See also

- `.github/workflows/project-tracker.yml`
- `workflow-templates/project-tracker.yml`
- `runbooks/triage.md`
- `.github/lib/labels.yml`
