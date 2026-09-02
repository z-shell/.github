# 22. Enforce Issue Traceability on the Pull Request, Not the Branch Name

- **Status:** PROPOSED
- **Date:** 2026-09-02
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

`decisions/0019-trunk-on-main-default.md` specifies short-lived
`feature-<id>`, `bug-<id>`, and `hotfix-<id>` branches. The stated purpose is
issue-linked topic-branch naming, so that every change on `main` can be traced
back to the work item that justified it.

That clause was unenforced until recently.
[#575](https://github.com/z-shell/.github/issues/575) found that the workflow
carrying it had never started successfully: 53 of 53 runs recorded
`startup_failure`, so no branch name was ever checked.
[#586](https://github.com/z-shell/.github/pull/586) fixed the workflow and
[#591](https://github.com/z-shell/.github/pull/591) registered its three
contexts in the `main` ruleset. `Validate Branch Name` became blocking for the
first time, and the organization's actual naming practice became visible as a
merge blocker rather than a convention.

### What the practice looks like

Across the last 60 merged pull requests into `z-shell/.github`:

| Branch shape      | Closes an issue | Mentions one only | No reference at all |
| ----------------- | --------------- | ----------------- | ------------------- |
| Has issue id (18) | 12              | 6                 | 0                   |
| No issue id (42)  | 10              | 22                | 10                  |

Read as a filter for traceability, the branch-name rule has perfect precision
and poor recall. Every one of the 18 branches carrying an id referenced an
issue somewhere. But the rule rejects 42 pull requests in order to catch the 10
that reference nothing, and in doing so blocks 32 that were traceable and
simply did not carry the number in the branch name.

The count of 32 is generous to the argument in one direction: "mentions one
only" counts any `#N` appearing in the pull-request body, so some of those are
passing references rather than deliberate links. It is conservative in another:
nothing currently checks the pull-request body at all, so the 10 untraceable
merges passed with no signal raised anywhere.

### Why the proxy is the wrong control point

A branch name is chosen before the work is understood, is frequently chosen by
a coding agent rather than the author, and is discarded on merge. A
pull-request reference is written when the change is complete, survives in the
permanent record, and is the artifact GitHub itself acts on for issue closure
and cross-linking.

Enforcing the proxy while leaving the real signal unchecked reproduces the
failure mode #575 described: a rule that exists as text where a mechanism was
believed to be enforcing it. Here the mechanism exists and enforces the wrong
predicate.

Raised in
[z-shell/.github#593](https://github.com/z-shell/.github/issues/593).

## Decision

Amend the branch-naming clause of ADR-0019. Every other part of ADR-0019
stands unchanged: trunk-based development on `main`, the class table, the
approved `zi` persistent-integration exception, the promotion contract, and the
migration steps.

### Traceability is enforced on the pull request

A required status check verifies that a pull request either closes an issue or
references one, or carries an explicit exemption. The check reports which of
the three applies, so an exempt pull request is a visible decision rather than
a silent gap.

Exemptions are explicit and narrow:

- an agreed repository label for work with no owning issue, such as gitlink and
  submodule reconciliation or a routine dependency update; and
- the automation prefixes already exempt from branch-name checking:
  `dependabot/`, `renovate/`, `copilot/`, and `codex/`.

An exemption label is a maintainer decision recorded on the pull request. An
agent may propose one; it does not apply one on its own authority.

### Branch names carry a type convention, not an identifier

`Validate Branch Name` becomes a shape check. A branch head must be either:

- `<type>-<id>` optionally followed by a lowercase slug, where `<type>` is
  `feature`, `bug`, or `hotfix`; or
- `<type>/<slug>`, where `<type>` is drawn from the Conventional Commits type
  set of `decisions/0003-conventional-commits.md` plus `feature`, `bug`, and
  `hotfix`.

`feature-<id>`, `bug-<id>`, and `hotfix-<id>` remain the recommended form and
stay valid. The identifier stops being mandatory. `next` keeps its exemption as
`zi`'s persistent integration branch.

### Ordering

The pull-request check lands and is observed on a real pull request before the
branch-name pattern relaxes. Relaxing first would leave a window with neither
control active, which is the state this record exists to end.

## Migration

1. Agree the exemption label and record it in `runbooks/labels.md`.
2. Implement the pull-request traceability check in
   `.github/workflows/commit-lint.yml` and verify it on a real pull request,
   because `runbooks/branch-protection.md` notes that GitHub only accepts
   status-check contexts it has already observed.
3. Register the new context in the `main` ruleset alongside the existing three.
4. Relax `Validate Branch Name` to the shape check above, in this repository
   and in `z-shell/zi`, which carries the same job with its patterns inlined.
5. Add a pointer in ADR-0019's Decision section recording that its
   branch-naming clause is amended here. This step belongs to the
   implementation, not to this draft: ADR-0019 is unamended until a maintainer
   accepts this record.
6. Update `AGENTS.md` where it describes issue-linked branch naming.

## Consequences

### Positive

- The control matches the goal. A pull request that references no work item is
  the thing that gets caught, rather than a branch name that failed to encode
  one.
- Roughly 32 of the last 60 merged pull requests would stop being blocked for a
  reason unrelated to whether the work was traceable.
- Agent-generated branch names stop being a policy problem, because the
  identifier they cannot supply is no longer where traceability lives.
- The exemption is explicit, so issue-free work such as gitlink reconciliation
  has a recorded answer instead of an admin bypass.

### Costs and risks

- One more required check on every pull request, and a label whose misuse would
  quietly restore the current gap. The check should report the exemption in its
  output so the label is visible in review rather than silent.
- Branch names lose an at-a-glance issue number. The pull-request reference and
  the closing keyword carry it instead, which is where GitHub reads it anyway.
- A pull request opened before its issue exists needs the issue filed before
  merge. That is the intended behaviour, and it is the step the current rule
  pushes to branch-creation time, which is earlier than the author usually
  knows what they are doing.
- `z-shell/zi` must move in step or the two enforcement copies drift again.

## Alternatives considered

- **Keep the identifier mandatory and change the naming habit.** Rejected. It
  rejects 32 traceable pull requests out of 42 to catch 10 untraceable ones,
  and it still leaves the real predicate unchecked, so the 10 would continue to
  merge once their branch names complied.
- **Relax the branch pattern without adding the pull-request check.** Rejected.
  That returns to the observed baseline where roughly a sixth of merges
  reference nothing at all, with no mechanism watching. This is precisely the
  #575 failure mode.
- **Drop branch-name checking entirely.** Rejected. A type prefix is nearly
  free to enforce, keeps branch listings readable, and gives the automation
  prefixes a defined place. Removing it buys nothing that the relaxed shape
  check does not already give.
- **Require a closing keyword specifically, rather than any reference.**
  Rejected. Partial work, sub-issues, and pull requests under a parent issue
  legitimately reference without closing. Requiring closure would push authors
  toward keywords that close issues prematurely.
- **Enforce traceability only by review.** Rejected on the evidence of this
  record: 10 of 60 merged pull requests referenced no issue while review was
  the only control.

## References

- `decisions/0003-conventional-commits.md`
- `decisions/0019-trunk-on-main-default.md`
- `runbooks/branch-protection.md`
- `runbooks/labels.md`
- `runbooks/project-tracker.md`
- [z-shell/.github#575](https://github.com/z-shell/.github/issues/575)
- [z-shell/.github#586](https://github.com/z-shell/.github/pull/586)
- [z-shell/.github#591](https://github.com/z-shell/.github/pull/591)
- [z-shell/.github#592](https://github.com/z-shell/.github/issues/592)
- [z-shell/.github#593](https://github.com/z-shell/.github/issues/593)
- [Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)
