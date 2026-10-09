<!-- GENERATED from knowledge/domains/governance/security-incident-response.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# Runbook — Security Incident Response

How to handle a security report from intake to post-incident review. This
operationalizes `decisions/0010-security-incident-response.md`. For reporter-facing
policy, see `.github/SECURITY.md`.

**Hard rule:** never handle exploit details on a public thread. Move them to a
private channel immediately and keep them there until a fix is published.

## Step 1 — Intake and acknowledge

1. Confirm the report arrived through a private channel — prefer GitHub
   **repository Security Advisories** ("Security" tab → "Report a vulnerability"),
   which gives a private draft advisory, a private collaboration space and fork,
   and CVE issuance. If it landed on a public issue/PR, hide exploit details and
   move it into a draft advisory.
2. Assign an incident owner — by default the security contact (currently
   **ss-o**), unless reassigned.
3. Acknowledge to the reporter within **3 business days**.
4. Track the incident in the draft GitHub Security Advisory (GHSA), not a public
   issue — public repos have no private issues. Keep exploit details in the GHSA
   only.

## Step 2 — Triage severity

Within **5 business days**, assign a severity using impact × exploitability and
apply the time-to-fix target. The canonical severity→target table lives in
`decisions/0010-security-incident-response.md` ("Severity and remediation
targets") — use it as the single source rather than duplicating it here.

Record which repos/artifacts are affected and the blast radius (interactive
shell? CI container? a single plugin?).

## Step 3 — Escalate if needed

- If the owner cannot act within the acknowledgement SLA, escalate to another org
  maintainer.
- For Critical incidents, consider an immediate temporary mitigation before the full fix: withdraw an artifact through its supported channel, pin a vulnerable dependency, or disable affected functionality. Do not move or reuse a published version tag (ADR-0010).

## Step 4: Remediate privately and record evidence

1. When using a temporary private fork, keep remediation branches and pull requests there. Follow the affected repository's branch model (ADR-0019); do not push the fix to a public branch to obtain CI. Keep the reporter updated in the draft advisory.
2. GitHub integrations, including CI, cannot access temporary private forks, and status checks do not run on their pull requests. Run the repository's applicable validation locally on the exact private head, including a regression test where the class allows it (ADR-0009). Record the full head SHA, commands, results, tool versions, skipped or unavailable checks, and their effect on confidence in the draft advisory. Local evidence does not make unavailable hosted checks pass. A changed head requires renewed validation and review.
3. Review the complete private diff under the repository's review policy. Record the reviewed head, findings and their disposition in the advisory. Use an authorized reviewer with advisory access; do not expose the private diff through public review services. The CI limitation alone does not waive the review requirement.
4. A separately authorized public CI-only pull request is permissible only after checking its complete diff and public metadata for vulnerability or remediation details. It must follow normal public checks and review, and cannot establish that the private remediation passed CI. Keep disclosure-bearing documentation and parent-workspace gitlink changes private until the remediation is merged and the coordinated publication gate below is satisfied.

See GitHub's [temporary-private-fork documentation](https://docs.github.com/en/code-security/tutorials/fix-reported-vulnerabilities/collaborate-in-a-fork) for platform behavior and UI steps. Record the unavailable-CI exception and exact local evidence in the draft advisory, not a public issue or pull request.

### If branch protections block advisory merge

GitHub documents that advisory merges do not enforce branch protection rules, while [the recorded incident in #569](https://github.com/z-shell/.github/issues/569#issuecomment-5462031843) encountered a ruleset block. Verify the actual merge path and effective rules before acting; do not assume either behavior applies universally.

Stop and request a separate maintainer decision when protections block publication. Any proposed temporary exception must identify the affected repository, exact rule or ruleset, minimal change, restoration procedure and verification. This runbook grants no standing bypass or permission to disable protections. If an exception is explicitly authorized, retain the original configuration privately, limit it to the approved merge, immediately restore it even if the merge fails, and verify the restored configuration and effective rules on the target branch. Record the outcome and any restoration failure in the advisory; a failed restoration requires immediate maintainer escalation.

## Step 5: Publish and disclose in order

Each outward-facing action needs explicit authorization for that action and repository. Approval of a remediation pull request does not authorize advisory merge, a tag or release, advisory publication, public documentation, parent gitlink publication, or a settings change. Check existing repository automation before merging: a merge may trigger deployment or release, so include those consequences in the maintainer's publication decision (including ADR-0039's separate signed-milestone authorization for Zi).

1. Obtain authorization to merge through the draft advisory after exact-head validation and review are complete. Confirm all open private-fork pull requests and the complete combined change are intended and mergeable: GitHub merges them together through the advisory, rather than merging individual private-fork pull requests. Verify the resulting target-branch commit.
2. Where a patched release is applicable, obtain its authorization and follow the owning repository's [release procedure](release.md). Validate the exact publication commit and verify the new patched tag and artifact refer to the intended fix. Never move or reuse a published version tag. For Git-consumed source repositories, verify the fix reached the publication branch; do not invent a release requirement.
3. Coordinate timing with the reporter under [SECURITY.md](../.github/SECURITY.md). Publish the advisory only with explicit authorization and after the fix is available through the repository's publication model. Credit the reporter unless they request anonymity; keep restricted reporter data and unpublished exploit details private.
4. Publish disclosure-bearing documentation and reconcile parent-workspace gitlinks only after the private remediation is merged and coordinated disclosure is authorized. Each repository's publication remains separately authorized and validated. Verify public references resolve to the intended patched revision; do not publish a private-fork ref or suggest that a parent gitlink update ships a release.

Record the authorization, exact revisions, validation and publication results in the draft advisory or its access-controlled incident record. If a gate cannot be satisfied, keep the remaining actions pending and record the blocker rather than advancing the sequence.

## Step 6 — Post-incident review (Critical / High)

Write a short review and retain it in the access-controlled incident record when it contains exploit details or reporter data. Only a sanitized version belongs in a public repository or tracker (never only in ephemeral notes):

- timeline (reported → acknowledged → triaged → fixed → disclosed)
- root cause
- the fix and any mitigation used
- one concrete follow-up action to prevent recurrence (file a tracker issue)

## Safe local lint diagnostics

Run Trunk through the repository wrapper so the linter process receives only a
documented minimal environment and disposable runtime directories:

```sh
automation/ci/trunk-safe-check.sh -- check --no-fix
```

The wrapper forwards only `CI`, `HOME`, `LANG`, `LC_ALL`, `NO_COLOR`, `PATH`,
`TERM`, `TMPDIR`, `TRUNK_CACHE`, `TRUNK_LAUNCHER_QUIET`, and the XDG cache,
config, and data locations. Directory values other than `PATH` are generated
inside a private temporary runtime directory. It does not forward GitHub
tokens, credentials, proxy settings, or unrelated caller variables. Do not put
secrets in command-line arguments.

If Trunk reports an internal tool-execution failure, the wrapper suppresses the
verbose diagnostic and deletes the runtime directory. Never print or attach a
raw Trunk failure report. If an earlier run exposed a credential-bearing value,
rotate that credential through its owning system and keep the incident details
in the access-controlled record.

## Anti-patterns

- discussing exploit details on a public thread
- silent fixes with no reporter coordination or credit
- skipping the post-incident review for a Critical incident
- leaving severity untriaged past the SLA
- invoking Trunk directly from a credential-bearing environment
- printing or attaching raw internal Trunk failure diagnostics

## See also

- `decisions/0010-security-incident-response.md`
- `.github/SECURITY.md`
- `runbooks/triage.md` (security-report special case)
- `runbooks/release.md`
