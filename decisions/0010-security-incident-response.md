# 10. Security Incident Response

- **Status:** PROPOSED
- **Date:** 2026-05-29
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

`.github/SECURITY.md` tells reporters _how to report_ a vulnerability and the
coordinated-disclosure expectation. It says nothing about what the org does once
a report arrives: who owns it, how fast it is acknowledged and triaged, how a fix
is shipped, and what happens afterward. Without that, response time and quality
depend on whoever happens to see the report.

The org ships shell that runs in users' interactive shells and a container image
used in CI, so a vulnerability can have broad blast radius. A written response
process — acknowledgement SLA, severity-based timelines, escalation, and a
post-incident review — closes the gap between "we accept reports" and "we handle
them predictably."

## Decision

### Intake channel

When an affected public repository exposes **Report a vulnerability**, reporters
use that private GitHub repository Security Advisory flow. If the option is not
available, reporters use a private contact method on the organization profile
and must not include vulnerability details in a public issue or pull request.

An authorized maintainer creates or uses a draft repository security advisory
as the access-controlled tracking record. A temporary private fork and a CVE
request are optional GitHub capabilities, not guaranteed outcomes.

### Ownership

An organization maintainer is the incident owner for each report. The owner
acknowledges, triages severity, coordinates the fix, and runs the post-incident
review. **ss-o** is the default incident owner. **wicoop** (named 2026-07-25) is
the backup incident owner.

Named 2026-07-25 (ss-o): backup access is granted per incident rather than
held standing. wicoop is an active org member as of 2026-07-25, with read
access on most repositories and admin access on `wiki`, but is not a member of
the `tsc` GitHub team that CODEOWNERS assigns as reviewer for this
organization. When the primary owner is available, they add wicoop as a
collaborator on the affected repository's draft security advisory at
escalation time, matching how GitHub advisory collaboration actually works
and avoiding standing access that would sit unused between incidents.

This has a real limit worth stating plainly: **as of 2026-07-25, ss-o is the
organization's only admin.** If ss-o specifically is the one who is
unreachable, there is no second admin to perform the access-grant step above,
and escalation is bounded by whatever access wicoop already holds until the
org has a second admin. This ADR does not claim that gap is closed; see
Escalation below for what that means in practice.

### Acknowledgement SLA

Confirmed 2026-07-25 (ss-o):

- Acknowledge a security report within **3 business days** of receipt.
- Triage to a severity within **5 business days**.

### Severity and remediation targets

Severity uses CVSS-style judgment (impact × exploitability). Confirmed
2026-07-25 (ss-o), the time-to-fix or documented-mitigation targets from
triage are:

| Severity | Examples                                      | Target      |
| -------- | --------------------------------------------- | ----------- |
| Critical | RCE, secret/credential exposure, supply-chain | **7 days**  |
| High     | Privilege escalation, auth bypass             | **30 days** |
| Medium   | Limited-scope info disclosure, DoS            | **90 days** |
| Low      | Hardening, defense-in-depth                   | Best effort |

Targets are goals, not guarantees; the owner records the rationale when a target
slips.

### Escalation

If the owner cannot act within the acknowledgement SLA, escalate to wicoop.
The owner grants wicoop collaborator access on the affected repository's
draft security advisory at that time (see Ownership above). If the owner
cannot act specifically because ss-o (the org's only admin as of 2026-07-25)
is unreachable, no one else in the org can perform that grant, and wicoop
responds using whatever access they already hold until the org has a second
admin.

Critical incidents are worked immediately. Before the full fix, prefer a
coordinated private mitigation, disabling or pinning affected functionality,
and channel-supported withdrawal, deprecation, or artifact revocation. Publish
a new patched version tag when a release is required. Never move or reuse a
published version tag.

### Remediation and disclosure

- Fixes land through the normal branch model (ADR-0019); critical fixes may use a
  `hotfix-<id>` branch from the publication branch.
- Coordinate disclosure with the reporter per `.github/SECURITY.md`: no public disclosure
  until a fix is published or the report is declined, and credit the reporter.
- Where a release artifact exists (ADR-0007 class 2), cut a patched tag and note
  the security fix in the release notes.
- Keep exploit details and reporter data in the advisory or another
  access-controlled record. Only a sanitized review or follow-up may be public.

### Post-incident review

For Critical and High incidents, the owner writes a short post-incident review:
timeline, root cause, fix, and a follow-up action to prevent recurrence. The
full review remains access-controlled when it contains exploit details or
reporter data; only a sanitized version may be placed in a public repository or
tracker.

### Administrative verification

Verified 2026-07-25 (ss-o), via the GitHub API:

- **Private vulnerability reporting:** enabled on all 86 public, non-fork
  repositories in the org. Not applicable to the 2 private repositories
  (`.github-private`, `.trunk`); GitHub only exposes this feature on public
  repositories, since its purpose is letting reporters without write access
  report privately.
- **Release immutability:** not enabled anywhere sampled. The two repositories
  that have actually cut a release (`zsh-lint`, packaged `zsh`) both show
  `immutable: false` on their only release (`v1.0.0`, 2022). This is a real
  gap, not an oversight in this ADR: if the org wants immutable releases, it
  needs to be turned on, most usefully before the next tag on a release-cutting
  repository.
- **Advisory/backup-access notifications:** not verifiable through the
  repository or organization API; these are the incident owner's personal
  GitHub notification settings, not an administrative setting this ADR can
  audit. Confirming them is a manual step for whoever holds the role.
- **Backup incident contact:** named 2026-07-25 (ss-o); see the Ownership
  section above and checklist item 2 below.

## Decision review required

This ADR remains **PROPOSED**. Before acceptance, a maintainer must:

1. [x] Confirm the proposed 3/5-business-day acknowledgement and triage
       targets and the 7/30/90-day remediation targets. Confirmed 2026-07-25
       (ss-o); see the SLA and severity sections above.
2. [ ] Name a backup incident contact and verify that contact's repository and
       advisory permissions. Named 2026-07-25 (ss-o): wicoop, an active org
       member. Left open rather than checked: standing permissions were
       deliberately not pre-verified (access is granted per incident instead,
       see Ownership above), and that model has a real gap when ss-o, the
       only admin, is the one who is unreachable. "Verify permissions" as
       written implies a pre-check this ADR does not claim to have done.
3. [x] Confirm where private vulnerability reporting, notifications, and
       release immutability are enabled or required. Confirmed 2026-07-25
       (ss-o); see the Administrative verification section above. Private
       vulnerability reporting is fully enabled; release immutability is
       verified off in both release-cutting repositories sampled (`zsh-lint`,
       packaged `zsh`) and remains a rollout gap if the org wants it;
       notifications are a personal setting outside this ADR's audit scope.
4. [ ] Accept, amend, supersede, or reject this proposal and record the
       decider and decision date.

Items 1 and 3 are resolved. Item 2 is named but deliberately left open: the
backup contact exists and the access model is decided, but standing
permissions were never verified and the single-admin gap means escalation is
not fully operational yet. Item 4, the actual accept, amend, or reject
decision, is a maintainer call this ADR cannot make for itself.

## Consequences

- If accepted and its rollout gaps are closed, reports get a predictable
  acknowledgement and remediation path instead of ad-hoc handling.
- `runbooks/security-incident-response.md` would be reconciled after acceptance;
  it is not changed by this draft.
- `.github/SECURITY.md` remains the reporter-facing entry point and would be
  reconciled after acceptance; this ADR defines the proposed internal response.
- Sanitized post-incident reviews build durable security memory without exposing
  restricted report data.

## Alternatives considered

- **Keep only `.github/SECURITY.md`.** Rejected: it covers intake but leaves
  response undefined, which is where time is actually lost.
- **Adopt a formal external framework (e.g. full ISO/NIST IR process).** Rejected
  as disproportionate for a small-maintainer OSS org; this ADR takes the
  load-bearing pieces (SLA, severity targets, escalation, review) without the
  overhead.
- **Per-repo security policies.** Rejected: vulnerabilities often span repos
  (shared loader, container, plugins); one org-level process avoids gaps.

## References

- `.github/SECURITY.md` — reporter-facing reporting and disclosure policy.
- `runbooks/security-incident-response.md` — step-by-step responder runbook.
- `decisions/0007-release-publication-flow.md` — how patched releases are cut.
- `decisions/0019-trunk-on-main-default.md` - hotfix branching for critical fixes.
- [GitHub repository security advisories](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/repository-security-advisories)
- [Configuring private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [Issue #454](https://github.com/z-shell/.github/issues/454) — dated control-gap
  evidence and maintainer decision record.
