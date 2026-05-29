# 10. Security Incident Response

- **Status:** PROPOSED
- **Date:** 2026-05-29
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

`.github/SECURITY.md` tells reporters *how to report* a vulnerability and the
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

### Ownership

An org maintainer is the incident owner for each report. The owner acknowledges,
triages severity, coordinates the fix, and runs the post-incident review. By
default the accepting maintainer (**ss-o**) owns incidents unless explicitly
reassigned.

### Acknowledgement SLA

- Acknowledge a security report within **3 business days** of receipt.
- Triage to a severity within **5 business days**.

### Severity and remediation targets

Severity uses CVSS-style judgment (impact × exploitability). Target time-to-fix
or documented mitigation from triage:

| Severity | Examples                                          | Target          |
| -------- | ------------------------------------------------- | --------------- |
| Critical | RCE, secret/credential exposure, supply-chain     | **7 days**      |
| High     | Privilege escalation, auth bypass                 | **30 days**     |
| Medium   | Limited-scope info disclosure, DoS                | **90 days**     |
| Low      | Hardening, defense-in-depth                       | Best effort     |

Targets are goals, not guarantees; the owner records the rationale when a target
slips.

### Escalation

If the owner cannot act within the acknowledgement SLA, the report is escalated
to another org maintainer. Critical incidents are worked immediately and may
warrant a temporary mitigation (yank a tag, pin a dependency, disable a workflow)
before the full fix.

### Remediation and disclosure

- Fixes land through the normal branch model (ADR-0008); critical fixes may use a
  `hotfix-<id>` branch from the publication branch.
- Coordinate disclosure with the reporter per `SECURITY.md`: no public disclosure
  until a fix is published or the report is declined, and credit the reporter.
- Where a release artifact exists (ADR-0007 class 2), cut a patched tag and note
  the security fix in the release notes.

### Post-incident review

For Critical and High incidents, the owner writes a short post-incident review:
timeline, root cause, fix, and a follow-up action (often a tracker issue) to
prevent recurrence. The review is kept in the owning repo or the tracker, not in
ephemeral notes.

## Consequences

- Reports get a predictable acknowledgement and remediation path instead of
  ad-hoc handling.
- `runbooks/security-incident-response.md` operationalizes this ADR step by step.
- `SECURITY.md` remains the reporter-facing entry point; this ADR governs the
  internal response.
- Post-incident reviews build durable security memory and feed the tracker.

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
