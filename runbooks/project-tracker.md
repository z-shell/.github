# Runbook — Project tracker

Use this runbook for the organization-wide task tracking in Linear.

## Tracker identity

- Workspace: `ss-o`
- URL: `https://linear.app/ss-o/`

## What belongs on the tracker

Track issues that need cross-repository or maintainer-level attention:

- cross-repository work
- release blockers
- security-sensitive work
- strategic or roadmap work
- organization infrastructure work

Do not add ordinary single-repository bugs, support questions, or small cleanup tasks just because they are actionable.

## Syncing with GitHub

Linear natively integrates with GitHub issues and pull requests.
We rely on Linear's built-in GitHub integration rather than maintaining custom GitHub Actions workflows.

1. Create or choose a test issue in the repository.
2. Because of the native integration, any issue matching the configured criteria in Linear will automatically be ingested.
3. You can manage and prioritize the issue directly from Linear.

## Verification

If an issue does not sync to Linear:

1. Verify the Linear GitHub integration settings are active for the specific repository.
2. Ensure you have not hit rate limits or permission boundaries.
3. Contact an organization admin if the repository needs to be manually added to the integration.

## See also

- `AGENTS.md`
- `runbooks/triage.md`
