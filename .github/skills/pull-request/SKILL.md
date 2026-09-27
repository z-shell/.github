---
name: pull-request
description: Prepare or update z-shell pull requests, inspect CI and review state after new commits, and hand off merge readiness using the canonical PR runbook. For reviewing code alone, use code-review.
---

# Pull requests

Read the routed canonical `runbooks/pull-requests.md` before acting. If it is unavailable locally, read the [public PR runbook](https://github.com/z-shell/.github/blob/main/runbooks/pull-requests.md). It owns branch planning, issue traceability, review, merge and post-merge procedures. If neither source is accessible, report the gap and do not perform external writes.

- Resolve the owning issue, repository, base and current HEAD, then select the runbook's steps for the current lifecycle phase.
- Check the approved scope before Git, publication, review or metadata mutations. This skill and tool availability grant no authority.
- Use the existing [code-review skill](https://github.com/z-shell/.github/blob/main/.github/skills/code-review/SKILL.md) and the canonical criteria named by the runbook for substantive review; this skill routes the lifecycle rather than replacing that review.
- After a push or rebase, refresh the latest commits, complete PR diff, CI results, annotations and review threads. Apply the runbook's current-HEAD review requirements; earlier evidence does not verify new commits.
- Check stored bodies and metadata after authorized writes. For review publication, follow the runbook's rendering and evidence requirements.
- Hand off the verified HEAD, check and review status, unresolved decisions and retained follow-ups. Stop at any unapproved merge, closure or cleanup boundary; follow the runbook's post-merge verification when authorized.
