# Runbook — Dependency Management

Use this runbook to configure or troubleshoot dependency automation across
Z-Shell repositories.

## Ownership boundary

Z-Shell uses two services with separate responsibilities:

| Service           | Responsibility                                                            |
| ----------------- | ------------------------------------------------------------------------- |
| GitHub Dependabot | Dependency graph, vulnerability alerts, and security update pull requests |
| Renovate          | Routine dependency version update pull requests                           |

Do not configure both services to create routine version updates in the same
repository. The split avoids duplicate pull requests, lock-file conflicts, and
unnecessary CI runs.

The governing proposal is
`decisions/0012-hybrid-dependency-management.md`. Until that ADR is accepted on
`main`, ADR 0004 remains the accepted policy and rollout changes should stay on
their feature branch.

## Required GitHub security settings

For every actively maintained repository, enable:

1. dependency graph;
2. Dependabot alerts;
3. Dependabot security updates.

These are GitHub repository or organization security settings. They are not
enabled by `renovate-config.json`, and they do not require a
`.github/dependabot.yml` file.

## Renovate organization preset

Routine update policy lives in the public organization repository:

```text
z-shell/.github/renovate-config.json
```

Renovate discovers this preset during organization onboarding. A repository may
also reference it explicitly:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

Keep repository configuration small. Add `renovate.json` only for a real
exception, such as a non-default target branch:

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"],
  "baseBranches": ["next"]
}
```

Custom managers and specialized package grouping also belong in the repository
that needs them.

## Migrating a repository

Do not remove Dependabot version updates until Renovate coverage is proven.

1. Confirm the Renovate GitHub App has access to the repository.
2. Confirm Renovate opens an onboarding/configuration pull request or processes
   the repository using the organization preset.
3. Confirm dependency graph, Dependabot alerts, and Dependabot security updates
   remain enabled in GitHub settings.
4. Add a minimal `renovate.json` only when the repository needs an override.
5. Delete `.github/dependabot.yml` to stop routine Dependabot version updates.
6. Confirm subsequent routine update pull requests come only from Renovate.

The safe migration set is the intersection of repositories with Renovate App
coverage and repositories currently containing `.github/dependabot.yml`.

## Validation

Validate the shared preset or a repository override with Renovate itself:

```sh
npx --yes --package renovate renovate-config-validator renovate-config.json
```

For a repository override, replace the final path with `renovate.json`.
`jq empty` checks JSON syntax, but it does not prove that Renovate recognizes
every option.

## Duplicate pull requests

If both bots open routine updates:

1. identify which package and manager overlap;
2. confirm Renovate is processing the shared preset;
3. remove the matching Dependabot version-update entry or the whole
   `.github/dependabot.yml`;
4. close the duplicate pull request only after choosing the update to retain.

Dependabot security update pull requests are expected and are not an overlap
with Renovate's routine update ownership.

## Rollback

If Renovate cannot access or process a repository:

1. restore that repository's last known-good `.github/dependabot.yml`;
2. validate its ecosystems, directories, schedule, and target branch;
3. investigate Renovate App access or preset validation;
4. remove the temporary Dependabot version-update configuration only after
   Renovate coverage is healthy again.

## See also

- `decisions/0004-dependabot-unification.md`
- `decisions/0012-hybrid-dependency-management.md`
- `renovate-config.json`
- `runbooks/new-repository.md`
