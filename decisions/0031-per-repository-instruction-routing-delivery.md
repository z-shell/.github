# 31. Deliver Instruction Routing Into Every Repository and Verify Vendored Skill Pins Mechanically

- **Status:** PROPOSED
- **Date:** 2026-09-26
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0014](0014-portable-agent-instruction-architecture.md) made this
repository's `AGENTS.md` the canonical organization baseline, required every
active instruction surface to be declared in
`.github/instruction-surfaces.json`, and required that mandatory policy reach
every supported runtime without depending on an optional hook, agent, or skill.
Point 9 of that decision left runtime discovery as a manual check.

The architecture is sound and its machinery works where it is installed. What
it does not do is reach the other repositories. Two measurements show the gap.

### Routing never arrives in a repository that is not this one

Every supported runtime discovers instructions from the Git root of its working
directory downward. Each repository in the organization is its own Git root.
A session opened in a repository therefore loads that repository's `AGENTS.md`
and nothing above it.

The `Required instruction routing` section, the text that sends a runtime to
`.github/instruction-surfaces.json`, exists only in this repository's
`AGENTS.md`. A survey of the fifteen organization repositories found:

| Repository                     | `AGENTS.md` lines | Names the routing manifest |
| ------------------------------ | ----------------- | -------------------------- |
| `z-shell/.github`              | 187               | yes                        |
| `z-shell/wiki`                 | 106               | no                         |
| `z-shell/F-Sy-H`               | 102               | no                         |
| `z-shell/zsh-eza`              | 91                | no                         |
| `z-shell/zsh-lint`             | 79                | no                         |
| `z-shell/zpmod`                | 54                | no                         |
| `z-shell/z-a-meta-plugins`     | 50                | no                         |
| `z-shell/zi`                   | 43                | no                         |
| `z-shell/src`                  | 31                | no                         |
| `z-shell/zsh-fancy-completions`| 26                | no                         |
| `z-shell/zd`                   | 13                | no                         |
| `z-shell/zsh`                  | 12                | no                         |
| `z-shell/zunit`                | 7                 | no                         |
| `z-shell/z-a-default-ice`      | absent            | no                         |
| `z-shell/z-a-eval`             | absent            | no                         |

Most of these files link to organization policy in prose, between one and eight
mentions each. A prose link is not a routing directive: it tells a reader where
policy lives, it does not tell a runtime to select and read the matching
required surfaces before acting. Two repositories carry no agent instructions
at all, so a session there receives nothing.

Session telemetry over the recorded history agrees. Of 225 sessions, 188 never
opened the routing manifest: 170 of 182 `codex` sessions and 18 of 43
`claude-code` sessions. The runtime that more often carries hook context reads
the manifest far more often, which is consistent with delivery, not preference,
being the variable.

### A vendored skill has no currency check

Twelve repositories vendor `.github/skills/code-review/SKILL.md` through
`gh skill install --pin`, which is what hosted Copilot review requires. Hashing
each copy with its injected frontmatter `metadata:` block removed shows all
twelve bodies are byte-identical to each other and differ from this
repository's canonical copy only by that metadata. The pins, however, disagree:
ten repositories pin one commit and two pin another, and neither is the current
canonical revision.

No automation reconciles a vendored copy against its source. No workflow in any
of the fifteen repositories performs that check. `runbooks/org-review.md`
already records why the obvious tool does not close the gap: `gh skill update
--dry-run` skips pinned skills, so its output cannot establish currency. The
organization baseline makes review-skill source currency and local drift a
mandatory health dimension, and today that dimension can only be assessed by
hand, which means in practice it is not assessed.

Both findings are the same defect in different clothing. ADR-0014 point 7 says
mandatory policy must not rely on an optional mechanism, and the private
overlay states the operative rule directly: where a runtime default can
override a rule that exists only as text, enforce the rule mechanically
instead. Routing delivery and pin currency are both rules that exist only as
text.

## Decision

1. **Every organization repository carries a generated routing preamble.**
   Each repository's `AGENTS.md` begins with a delimited, generated block that
   names this repository as the canonical policy owner, states the routing
   obligation in the same terms as the organization baseline, and enumerates
   that repository's own declared surfaces. It is bounded by
   `<!-- BEGIN org-routing -->` and `<!-- END org-routing -->` markers, matching
   the delimited-composite convention ADR-0014 point 4 established.

2. **The preamble is generated, never hand-written.** Content outside the
   markers is repository-owned and is never modified by generation. A
   repository with no `AGENTS.md` receives one consisting of the preamble plus
   a minimal repository-owned body. This preserves ADR-0014 point 1: the
   generated block routes, it does not restate policy, so the canonical
   baseline remains the single standalone source.

3. **This repository owns the generator.** A script here produces the preamble
   for a target repository from the canonical manifest. No second copy of the
   generation logic exists in any consuming repository, and no consuming
   repository may edit the generated region.

4. **Delivery is a reusable workflow each repository calls.** This repository
   publishes a `workflow_call` workflow that regenerates the preamble for the
   calling repository and fails the check when the committed region differs
   from the generated one, or when a declared surface is missing. Thirteen of
   the fifteen repositories already consume organization reusable workflows, so
   this uses an established and understood delivery path rather than a new one.

5. **Vendored skill pins are verified against an approved canonical revision.**
   Vendoring continues, because hosted Copilot review reads the in-repository
   copy. The same reusable workflow compares each vendored skill's recorded
   `github-pinned` revision against the canonical revision this repository
   declares as approved, and compares the vendored body against the canonical
   body with the installer's metadata block excluded. A mismatch in either
   dimension fails the check and names the remedy. This converts the
   source-currency and local-drift dimensions of `runbooks/org-review.md` from
   manual assessment into a deterministic result.

6. **The approved canonical skill revision is declared, not inferred.** This
   repository records the revision downstream repositories are expected to pin.
   Advancing it is a reviewed change here, and downstream re-pinning follows the
   existing authorized-installation procedure in `runbooks/org-review.md`.
   Nothing in this decision authorizes automated commits to another repository.

7. **The check reports, it does not self-heal.** A drift failure names the
   file, the expected content or revision, and the command that fixes it.
   Remediation in another repository remains a separate authorized change,
   consistent with the organization rule that health evaluations only propose
   remediation.

8. **Runtime discovery remains a manual check.** ADR-0014 point 9 is unchanged.
   This decision makes delivery verifiable in the repository; it does not claim
   to prove that a runtime read what was delivered. The session measurement
   above is evidence of a delivery gap, not a discovery guarantee once the gap
   is closed.

Material changes under this decision follow the impact review in
`runbooks/instruction-update.md`.

## Consequences

### Positive

- A session starting in any organization repository receives the routing
  obligation, which today reaches only sessions that start in this repository.
- Instruction ownership stays centralized while delivery becomes local, which
  is what ADR-0014 intended and did not yet implement below the baseline.
- Skill drift and stale pins fail a check instead of waiting for a manual
  audit that the evidence shows is not happening.
- The two repositories with no agent instructions stop being silent gaps.
- Duplication becomes structurally impossible for the generated region: it has
  exactly one generator and a byte-comparison gate.

### Negative

- Fifteen repositories gain a required check, and a canonical routing change
  now produces a visible follow-up in each of them.
- The reusable workflow becomes a cross-repository dependency: a defect in it
  can block unrelated pull requests until it is fixed here.
- Advancing the approved skill revision becomes an explicit reviewed step
  rather than an implicit one, which is the intent but is also more work.
- Repositories pinning the reusable workflow by commit must bump that pin to
  receive generator fixes.

### Neutral

- The vendored-copy model is retained rather than replaced. Hosted review reads
  the repository's own tree, so a pointer would not serve it.
- The organization manifest remains the single inventory. This decision adds a
  delivery and verification path over it, and changes neither its schema
  authority nor the byte limit ADR-0014 point 8 set.

## Alternatives considered

1. **Leave routing in prose and ask repositories to link to policy.** Rejected:
   this is the current state, and the session measurement shows 188 of 225
   sessions did not reach the manifest under it. A link is not a directive.
2. **Require each repository to hand-write the routing stanza, with CI checking
   only that it is present.** Rejected: a presence check permits fifteen
   divergent wordings, which reproduces as textual drift exactly the
   duplication this decision exists to remove. ADR-0014 point 3 already
   rejected per-repository policy surfaces for the same reason.
3. **Generate child files from the private control workspace and push them.**
   Rejected: it places the generator outside the public canonical owner, makes
   correctness depend on a checkout no contributor or CI run has, and leaves an
   external contributor's pull request unverifiable. ADR-0014 point 1 requires
   public policy to be usable from a standalone clone.
4. **Rely on runtime hooks to inject routing at session start.** Rejected under
   ADR-0014 point 7: hook coverage is per-runtime and per-profile, 0 of 182
   `codex` sessions carried hook context, and a mandatory rule may not depend
   on an optional mechanism.
5. **Stop vendoring the review skill and reference the canonical copy.**
   Rejected: hosted Copilot review resolves the skill from the repository's own
   tree, so removing the copy removes the capability.
6. **Advance every pin automatically whenever canonical changes.** Rejected: it
   writes to repositories without review, and the organization requires that
   installation and update be separately authorized.

## References

- [z-shell/.github#660](https://github.com/z-shell/.github/issues/660): the
  decision request, with the repository survey and session measurements.
- [ADR-0014](0014-portable-agent-instruction-architecture.md): the instruction
  architecture this decision delivers below the baseline.
- [ADR-0001](0001-meta-repo-and-agents-md.md): the original `AGENTS.md` entry
  point.
- `AGENTS.md`: the canonical baseline and its routing requirement.
- `.github/instruction-surfaces.json`: the surface inventory the preamble is
  generated from.
- `runbooks/instruction-update.md`: the required impact review.
- `runbooks/org-review.md`: the review-skill readiness dimensions this decision
  makes deterministic, and the authorized installation procedure.
- `scripts/validate-agent-policy.py`: the existing public validator.
