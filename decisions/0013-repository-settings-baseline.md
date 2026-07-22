# 13. Repository Settings Baseline by Class

- **Status:** PROPOSED
- **Date:** 2026-07-22
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

The organization declares requirements that nothing verifies.

ADR-0009 states that class-2 repositories have a test suite that is
**required** and that **gates release tags**. `z-shell/zsh-lint` is class 2. Its
default branch reports:

```json
{ "required_status_checks": null, "required_approving_review_count": 0, "enforce_admins": false }
```

The requirement is real policy and is enforced by nothing. This is the same
failure recorded in #464, where two documents described a commit-trailer check
that no workflow ran, generalized from CI to repository configuration.

A survey of all 86 active, public, non-fork repositories found:

| Measure | Count |
| --- | --- |
| No rules at all on the default branch | **75 (87%)** |
| No classic branch protection | 60 (70%) |
| No rulesets | 73 (85%) |
| Any rule present | 11 — six of which have only `copilot_code_review` |
| Repositories with more than one kind of rule | **2** (`zi`, `wiki`) |
| Required status checks configured | `zi` 5, `wiki` 1, all others 0 |
| Default branch still `master` | `z-shell/web` |

The two configured repositories do not agree with each other, and neither was
derived from a written standard. Nothing in `decisions/`, `runbooks/`, or
`AGENTS.md` mentions branch protection or rulesets, and
`runbooks/new-repository.md` bootstraps labels, CI templates, and dependency
automation without ever configuring protection. Settings have therefore been set
per repository, by hand, at different times, against no shared reference.

Two mechanisms are in play simultaneously. Classic branch protection and
repository rulesets are **independent** systems whose effective behavior is
their union. `z-shell/wiki` reports `required_linear_history: false` under
classic protection while a ruleset enforces it on the same branch. Reading
either source alone gives a wrong answer, and 19 repositories still carry
classic protection with no ruleset at all.

**Organization-level rulesets are not available on the current plan**
(`GET /orgs/z-shell/rulesets` returns `403 Upgrade to GitHub Team`), and no
repository custom properties are defined. Central enforcement is therefore not
an option today: per-repository configuration is the only mechanism, so drift is
structural rather than accidental.

## Decision

Adopt a required settings baseline, expressed per ADR-0007 repository class, as
the reference that repositories are configured against and audited for.

### Baseline by class

Classes are exactly those defined in
`decisions/0007-release-publication-flow.md`, referred to here by number so the
table stays readable:

1. **Continuously deployed artifacts** — `wiki`, `src`, `zd` images
2. **Versioned tools and packages** — `zunit`, `zsh-lint`, packaged `zsh`
3. **Git-consumed source** — `zi`, most plugins and annexes
4. **Meta/infrastructure** — `.github`

`R` = required. `S` = recommended, not required.

| Setting | Class 1 | Class 2 | Class 3 | Class 4 |
| --- | --- | --- | --- | --- |
| Default branch named `main` | R | R | R | R |
| Pull request required to the default branch | R | R | R | R |
| Deletion of the default branch blocked | R | R | R | R |
| Force push to the default branch blocked | R | R | R | R |
| Required status checks | R | R | S | S |
| Linear history | R | S | S | S |
| Signed commits | S | S | S | S |
| Copilot code review | R | R | S | R |

Rationale for the differences:

- **Required status checks** are mandatory only where a failing artifact reaches
  users automatically (class 1) or is published under a version tag (class 2).
  Class 3 is consumed from source at a ref the consumer chooses.
- **Linear history** is required only for class 1, where the deployed branch must
  be trivially bisectable against what is live. Elsewhere it constrains merge
  strategy for little benefit — and see the cost recorded below.
- **Copilot code review** is required wherever a change reaches users or other
  repositories without a second human necessarily reading it.

### Expressed as rulesets, not classic protection

New configuration uses repository rulesets. Classic branch protection is treated
as legacy and is not extended.

Where both exist, **neither one is authoritative**: the two systems apply
simultaneously and the effective rule is their union. A ruleset does not
override, disable, or supersede classic protection — the classic settings keep
applying until they are explicitly removed. Any audit must therefore read both
sources, and a repository is only fully migrated once its classic protection is
deleted, not merely once a ruleset exists alongside it.

Migration of the 19 classic-only repositories is not required by this ADR and
should not be bundled with adopting the baseline. Until a repository is
migrated, expect its behavior to reflect both systems at once.

### Repositories with no CI

23 repositories have no workflow files. "Required status checks" is unsatisfiable
there. Those repositories are conformant on every other row and are reported as
`n/a` for that row rather than as failures.

## Rollout and rollback

1. Accept this ADR. It changes no repository by itself.
2. Add a settings step to `runbooks/new-repository.md` so new repositories start
   conformant.
3. Build a read-only audit that reports drift per repository against this table,
   following the `scripts/labels-sync.rb` pattern: read-only by default, an apply
   mode behind both `--apply` and `--confirm-apply`, and a pilot allowlist.
4. Apply per repository, deliberately, starting with class 1 and class 2.

Rollback is per repository and immediate: rulesets can be deleted without
touching repository contents. Nothing in this ADR is irreversible.

## Consequences

### Positive

- A declared standard exists, so "is this repository configured correctly?" has
  an answer that is not a matter of opinion.
- Drift becomes measurable. Given per-repository configuration is the only
  mechanism available on this plan, measurement is the only alternative to
  discovering gaps by accident.
- The declared-versus-enforced gap in ADR-0009 becomes visible rather than
  latent.

### Negative / costs

- Requiring pull requests on repositories that currently allow direct pushes will
  change day-to-day habits for single-maintainer repositories.
- Required status checks can deadlock. `z-shell/wiki` required a check whose
  failure could only be cleared by the merge that the check was blocking; the fix
  needed a direct-to-`main` commit. Any class-1 repository can reach this state,
  and the escape route must stay available.
- Rules do not stop administrators. An admin push reports
  `Bypassed rule violations` and succeeds. The baseline raises the floor; it does
  not make configuration self-enforcing.
- Configuring 86 repositories is real work even when automated, and every applied
  rule is a way to lock a maintainer out of their own repository.

### Neutral

- `enforce_admins` is deliberately left out of the baseline. Enabling it would
  have made the `wiki` deadlock unrecoverable without changing settings under
  pressure.
- The baseline says nothing about branch names other than the default, so
  ADR-0008's `next` branch model is unaffected.

## Alternatives considered

- **Organization-level rulesets.** The correct mechanism, and what this ADR would
  otherwise recommend instead of a per-repository baseline. Unavailable on the
  current plan; revisit if the organization moves to GitHub Team.
- **Do nothing and fix repositories as problems surface.** This is the status
  quo, and it is what produced a class-2 repository with an unenforced "required"
  test suite. The cost is paid in incidents rather than in setup.
- **One uniform policy for all repositories.** Simpler to state and to audit, but
  it would require status checks on 23 repositories that have no CI, and would
  impose class-1 constraints on plugins consumed from source.
- **Automated remediation across all repositories.** Rejected: applying
  protection unattended to 86 repositories risks locking maintainers out, and the
  labels rollout showed that a per-repository confirm step is affordable.

## References

- `decisions/0007-release-publication-flow.md` — the repository classes this
  baseline is keyed to.
- `decisions/0009-testing-ci-strategy.md` — declares the class-2 test requirement
  that is currently unenforced.
- `runbooks/new-repository.md` — bootstrap procedure that should gain a settings
  step.
- `runbooks/release.md` — records that classic protection and rulesets are
  independent systems whose effective rule is their union.
- `scripts/labels-sync.rb` — the audit-then-gated-apply pattern the eventual
  settings audit should follow.
