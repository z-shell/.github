# Runbook — Security Incident Response

How to handle a security report from intake to post-incident review. This
operationalizes `decisions/0010-security-incident-response.md`. For reporter-facing
policy, see `.github/SECURITY.md`.

**Hard rule:** never handle exploit details on a public thread. Move them to a
private channel immediately and keep them there until a fix is published.

## Step 1 — Intake and acknowledge

1. Confirm the report arrived through a private channel (security policy contact).
   If it landed on a public issue/PR, hide exploit details and move it private.
2. Assign an incident owner — by default the accepting maintainer (**ss-o**),
   unless reassigned.
3. Acknowledge to the reporter within **3 business days**.
4. Open a private tracking record (private issue or maintainer channel). Do not
   put exploit details in a public tracker item.

## Step 2 — Triage severity

Within **5 business days**, assign a severity using impact × exploitability:

| Severity | Examples                                      | Target time-to-fix |
| -------- | --------------------------------------------- | ------------------ |
| Critical | RCE, secret/credential exposure, supply-chain | 7 days             |
| High     | Privilege escalation, auth bypass             | 30 days            |
| Medium   | Limited-scope info disclosure, DoS            | 90 days            |
| Low      | Hardening, defense-in-depth                   | Best effort        |

Record which repos/artifacts are affected and the blast radius (interactive
shell? CI container? a single plugin?).

## Step 3 — Escalate if needed

- If the owner cannot act within the acknowledgement SLA, escalate to another org
  maintainer.
- For Critical incidents, consider an immediate temporary mitigation before the
  full fix: yank or move a tag, pin a vulnerable dependency, or disable an
  affected workflow.

## Step 4 — Remediate

1. Fix on a branch per ADR-0008. Critical fixes may use `hotfix-<id>` from the
   publication branch.
2. Add a regression test where the class allows it (ADR-0009).
3. For release-bearing repos (ADR-0007 class 2), cut a patched `vX.Y.Z` tag and
   note the security fix in the release notes.
4. Keep the reporter updated on progress.

## Step 5 — Disclose

- Coordinate timing with the reporter per `SECURITY.md`: no public disclosure
  until a fix is published or the report is declined.
- Credit the reporter unless they ask otherwise.
- After the fix ships, the public record (release notes / advisory) may describe
  the issue at the appropriate level of detail.

## Step 6 — Post-incident review (Critical / High)

Write a short review and store it in the owning repo or tracker (never only in
ephemeral notes):

- timeline (reported → acknowledged → triaged → fixed → disclosed)
- root cause
- the fix and any mitigation used
- one concrete follow-up action to prevent recurrence (file a tracker issue)

## Anti-patterns

- discussing exploit details on a public thread
- silent fixes with no reporter coordination or credit
- skipping the post-incident review for a Critical incident
- leaving severity untriaged past the SLA

## See also

- `decisions/0010-security-incident-response.md`
- `.github/SECURITY.md`
- `runbooks/triage.md` (security-report special case)
- `runbooks/release.md`
