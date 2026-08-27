# Runbook - Learning capture

Use this workflow before claiming non-trivial project work complete. Its purpose
is to prevent repeated investigation while keeping project knowledge concise,
evidence-based, and attached to the correct source of truth.

## Scope

Run the review after implementation, debugging, research, release, incident,
policy, architecture, documentation, or multi-repository work that required
meaningful judgment.

Treat a quick factual answer, routine formatting, a simple read-only lookup, or
an unchanged status check as trivial unless it revealed a reusable correction
or project constraint.

## Review questions

1. What was unexpectedly difficult, incorrect, repeated, or newly discovered?
2. Is the finding likely to affect a future task?
3. What evidence supports it?
4. Who needs the knowledge and at what repository scope?
5. Can the recurrence be prevented mechanically?
6. Which existing canonical surface owns the finding?
7. Does that surface already contain equivalent or contradictory guidance?

## Strong candidate signals

- an unexpected test, build, release, deployment, or tooling failure
- a maintainer correction or a disproved assumption
- a plausible approach that was rejected for a durable reason
- repeated investigation or the same finding in more than one repository
- a missing, stale, duplicated, or contradictory instruction
- a reusable command sequence or operational procedure
- meaningful deferred scope or a blocker that another session must resume
- a security, privacy, publication, or repository-boundary discovery

## Valid outcomes

- `No durable learning`: nothing should be written or reported.
- `Candidate identified`: report the evidence, scope, proposed owner, and
  required authority.
- `Existing owner updated`: name the canonical artifact and verification.
- `Deferred follow-up recorded`: link the owning issue, pull request, or
  tracker item.

`No durable learning` is a successful outcome. Never manufacture a lesson to
satisfy the workflow.

## Destination matrix

| Finding                                                       | Preferred owner                                                                |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| A recurrence that can be detected mechanically                | Code, test, type, schema, lint rule, validator, or script                      |
| A mandatory rule that applies broadly                         | Root `AGENTS.md`                                                               |
| Mandatory detail limited by task or path                      | Routed scoped instruction                                                      |
| A reusable multi-step agent workflow                          | Skill                                                                          |
| An implementation idiom observed in at least two repositories | `PATTERNS.md`                                                                  |
| A significant or difficult-to-reverse decision                | Proposed ADR                                                                   |
| A repeatable operational procedure                            | Runbook                                                                        |
| Active work, blocker, or deferred work                        | Owning GitHub issue or pull request, plus a linked Linear mirror when required |
| An unfinished session another agent must resume               | GitHub-native agent handoff                                                    |
| Durable long-form user or maintainer guidance                 | Appropriate documentation or wiki area                                         |
| A private maintainer preference or private heuristic          | Private memory, with explicit maintainer request or consent                    |
| A one-time detail already clear from code or history          | No additional artifact                                                         |

Prefer executable prevention over prose. Extend an existing canonical owner
instead of creating a second source of truth.

## Candidate quality gate

A candidate is ready for promotion only when all of these are true:

1. Evidence from the reviewed task is named, such as a failing command, review
   finding, corrected assumption, repeated search, or repository examples.
2. Future applicability is stated without claiming a universal rule from one
   unusual event.
3. The intended consumers and repository scope are explicit.
4. The canonical owner has been searched for duplicates and contradictions.
5. The smallest effective destination has been selected.
6. The proposed change is within the current task's authority.
7. Verification and an owner exist for any resulting action.

If any item is missing, keep the result as a candidate or discard it.

## Authority and privacy gate

- Do not write private memory unless the maintainer explicitly requested it or
  explicitly consented in the current session.
- Do not create external issues, pull requests, tracker updates, or published
  documentation without authority for that workflow.
- Do not edit another repository merely because it is the ideal destination.
  Report the candidate and request the required scope.
- Never store secrets, credentials, personal data, private hosts or addresses,
  or machine-specific state in public artifacts.
- A learning review does not broaden implementation, publication, merge,
  release, or cleanup authority.

## Completion reporting

Keep `No durable learning` internal unless the maintainer requests an audit
trail.

When a candidate matters, include a concise completion note:

```text
Learning candidate: <finding>
Evidence: <specific evidence>
Proposed owner: <canonical artifact>
Status: promoted | recorded for follow-up | approval required
```

A final response or handoff is not a durable owner by itself. When authority is
missing, identify the candidate and required destination without implying it
was captured.

Do not append this block when no candidate exists.

## Pilot evaluation

Review the first 30 non-trivial tasks or four weeks of use, whichever occurs
first. Measure:

- the number of reviewed tasks
- silent `No durable learning` outcomes
- candidates proposed
- candidates promoted, rejected, or merged into an existing owner
- repeated investigations that still occurred
- later tasks that reused a promoted item
- median review overhead
- stale or contradictory artifacts introduced

Do not add a command hook merely because one review was missed. Consider a
runtime reminder only when the measured omission rate exceeds 10 percent and a
prototype can keep false reminders below 10 percent without parsing an
unstable transcript format.

## See also

- `AGENTS.md`
- `.github/AGENT_MEMORY.md`
- `.github/instruction-surfaces.json`
- `PATTERNS.md`
- `decisions/`
- `runbooks/adr.md`
- `runbooks/instruction-update.md`
- `runbooks/project-tracker.md`
