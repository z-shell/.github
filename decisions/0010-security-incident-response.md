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
review. **ss-o** is currently the only documented maintainer and therefore the
proposed default incident owner. A named backup with verified access to the
affected repository and advisory is required before escalation is operational.

### Acknowledgement SLA

The proposed targets, subject to maintainer confirmation, are:

- Acknowledge a security report within **3 business days** of receipt.
- Triage to a severity within **5 business days**.

### Severity and remediation targets

Severity uses CVSS-style judgment (impact × exploitability). The proposed
time-to-fix or documented-mitigation targets from triage, also subject to
maintainer confirmation, are:

| Severity | Examples                                      | Target      |
| -------- | --------------------------------------------- | ----------- |
| Critical | RCE, secret/credential exposure, supply-chain | **7 days**  |
| High     | Privilege escalation, auth bypass             | **30 days** |
| Medium   | Limited-scope info disclosure, DoS            | **90 days** |
| Low      | Hardening, defense-in-depth                   | Best effort |

Targets are goals, not guarantees; the owner records the rationale when a target
slips.

### Escalation

If the owner cannot act within the acknowledgement SLA, use the named,
permission-verified backup route. Until that route exists, escalation is an
acknowledged rollout gap rather than an operational promise.

Critical incidents are worked immediately. Before the full fix, prefer a
coordinated private mitigation, disabling or pinning affected functionality,
and channel-supported withdrawal, deprecation, or artifact revocation. Publish
a new patched version tag when a release is required. Never move or reuse a
published version tag.

### Remediation and disclosure

- Fixes land through the normal branch model (ADR-0008); critical fixes may use a
  `hotfix-<id>` branch from the publication branch.
- Coordinate disclosure with the reporter per `SECURITY.md`: no public disclosure
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

As of the 2026-07-18 audit, private vulnerability reporting, advisory
notifications, backup access, and release immutability were not administratively
verified. This ADR does not claim that those controls are enabled.

## Decision review required

Before acceptance, a maintainer must:

1. Confirm the proposed 3/5-business-day acknowledgement and triage targets and
   the 7/30/90-day remediation targets.
2. Name a backup incident contact and verify that contact's repository and
   advisory permissions.
3. Confirm where private vulnerability reporting, notifications, and release
   immutability are enabled or required.
4. Accept, amend, supersede, or reject this proposal and record the decider and
   decision date.

## Consequences

- If accepted and its rollout gaps are closed, reports get a predictable
  acknowledgement and remediation path instead of ad-hoc handling.
- `runbooks/security-incident-response.md` would be reconciled after acceptance;
  it is not changed by this draft.
- `SECURITY.md` remains the reporter-facing entry point and would be reconciled
  after acceptance; this ADR defines the proposed internal response.
- Sanitized post-incident reviews build durable security memory without exposing
  restricted report data.

## Alternatives considered

- **Keep only `SECURITY.md`.** Rejected: it covers intake but leaves response
  undefined, which is where time is actually lost.
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
- `decisions/0008-branching-model.md` — hotfix branching for critical fixes.
- [GitHub repository security advisories](https://docs.github.com/en/code-security/concepts/vulnerability-reporting-and-management/repository-security-advisories)
- [Configuring private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
- [GitHub immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
- [Issue #454](https://github.com/z-shell/.github/issues/454) — dated control-gap
  evidence and maintainer decision record.
