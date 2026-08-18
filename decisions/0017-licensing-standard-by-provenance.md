# 17. Licensing Standard by Provenance and Consumption

- **Status:** ACCEPTED
- **Date:** 2026-08-18
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

The organization has no written licensing policy. Nothing in `decisions/`,
`runbooks/`, `AGENTS.md`, or `PATTERNS.md` states which license a repository
should carry, how a new repository chooses one, or what to do when an existing
repository disagrees with the rest. `runbooks/new-repository.md` bootstraps
labels, CI templates, and dependency automation without ever selecting a
license.

The intent that GPL-3 is the organization standard exists, but only as
maintainer preference that was never ratified into a decision record. This is
the same failure mode `decisions/0013-repository-settings-baseline.md` opens
with: a requirement that is real in intent and enforced by nothing.

A survey of eleven actively maintained repositories on 2026-08-17 found the
intent is not reflected in practice:

| License | Repositories                                                       |
| ------- | ------------------------------------------------------------------ |
| GPL-3   | `.github`, `wiki`, `src`, `z-a-meta-plugins`, `zsh-fancy-completions` |
| MIT     | `zi`, `zd`, `zsh-lint`, `zsh-eza`, `zunit`, `zsh`                    |

Two of the MIT repositories cannot be relicensed at all. `zunit` is
`Copyright (c) 2016 James Dinsdale` and `zsh` is
`Copyright (c) 2019 zsh-packages`; both carry third-party copyright that this
organization does not hold. A blanket GPL-3 rule marks them permanently
non-compliant against a requirement they can never satisfy, which trains
maintainers to ignore the finding.

`zi` is a different case again. It is organization-authored
(`Copyright (c) 2021, Salvydas Lukosius & Z-Shell ZI Community`) and could be
relicensed, since MIT explicitly grants sublicense rights. But it is a plugin
manager: third-party plugin code is `source`d into the same shell process.
Whether a plugin becomes a derivative work of a copyleft shell library it is
sourced into is unsettled, and that ambiguity is an adoption cost against
permissively licensed alternatives. It would also raise the same question for
the organization's own `z-a-*` annexes, which load through `zi`'s API.

Relicensing is also one-directional and prospective. MIT grants already made
cannot be revoked, so every published release stays permissively licensed and
forkable regardless of what a future release carries.

## Decision

Adopt a licensing standard expressed by provenance and consumption model,
rather than a single license value.

### Classes

**Class L1: organization-authored, not loaded into a user's shell.**
Infrastructure, documentation, container images, standalone tools, and CI
assets. **GPL-3 required.** Copyleft costs nothing here because the consumer
runs the artifact rather than linking their own code into it.

**Class L2: organization-authored, combined as source with a user's own shell
code.** Plugin managers, plugins, and annexes. **Permissive (MIT) by deliberate
choice.** The derivative-work boundary for sourced shell code is unsettled, and
the organization's own ecosystem depends on third parties loading this code
alongside their own.

The discriminator is source combination, not merely running in the shell
process. A compiled module is dlopened as a binary and is therefore L1, not L2.

**Class L3: third-party forks and repackaging.** **Upstream license retained,
never relicensed.** The organization does not hold the copyright.

### Assignments

| Repository              | Class | License | Action                       |
| ----------------------- | ----- | ------- | ---------------------------- |
| `.github`               | L1    | GPL-3   | compliant                    |
| `wiki`                  | L1    | GPL-3   | compliant                    |
| `z-a-meta-plugins`      | L2    | GPL-3   | documented L2 exception      |
| `zsh-fancy-completions` | L2    | GPL-3   | documented L2 exception      |
| `zi`                    | L2    | MIT     | compliant, deliberately      |
| `zunit`                 | L3    | MIT     | compliant, upstream retained |
| `zsh`                   | L3    | MIT     | compliant, upstream retained |
| `src`                   | L1    | GPL-3   | compliant, settled 2026-08-18 |
| `zd`                    | L1    | MIT     | relicense, approved          |
| `zsh-lint`              | L1    | MIT     | relicense, approved          |
| `zsh-eza`               | L2    | MIT     | compliant                    |

Every repository records its class, so a license becomes a deliberate recorded
choice rather than whatever the bootstrapping session happened to pick.

### Settled by the maintainer, 2026-08-18

**`src` is L1 and stays GPL-3.** A compiled module is dlopened as a binary
rather than merged as text into a user's script, so the sourced-script
derivative-work ambiguity that justifies permissive L2 does not arise. Being
loaded into the shell process is not sufficient on its own to make something
L2; the discriminator is whether third-party source is combined with it.

**`zd` and `zsh-lint` relicense from MIT to GPL-3.** Both are
organization-authored with no third-party copyright barrier, and neither is
sourced into a user's shell: `zd` is a container environment and `zsh-lint` is
a standalone analyzer. MIT permits sublicensing, so no contributor consent is
required, and every previously published release remains available under MIT.

**`z-a-meta-plugins` and `zsh-fancy-completions` stay GPL-3 as documented L2
exceptions.** L2 sets a default, not a prohibition. An existing copyleft
license inside L2 is preserved rather than reversed, because relicensing from
GPL-3 toward permissive is the direction that genuinely requires every
contributor's consent, unlike MIT toward GPL-3 which MIT's sublicense grant
already permits. New L2 repositories still start permissive.

## Consequences

**Upside.** Audit findings become actionable: `zunit` and `zsh` stop being
permanent violations, and the two genuine drifts (`zd`, `zsh-lint`) become a
short bounded task. New repositories get a class at bootstrap instead of an
accidental license. The reasoning is recorded, so the next person to ask "why
is the plugin manager permissive?" gets an answer instead of a rediscovery.

**Cost.** Three classes are more to carry than one rule, and the boundary
between L1 and L2 requires judgment for anything that is both a tool and a
shell integration. Class L2 forgoes copyleft protection on organization code
deliberately, which means a third party may ship a proprietary derivative of
`zi`. That is accepted as the price of being infrastructure other people build
on.

**Not addressed.** This ADR does not relicense anything by itself. Each
relicensing is a separate change with its own release note stating that prior
releases remain under the previous license.

## Alternatives considered

**Blanket GPL-3 across the organization.** Rejected. Two repositories carry
third-party copyright and cannot comply at any effort level, so the rule would
be born violated. It would also force a plugin manager into a copyleft position
whose derivative-work boundary is unsettled, for a benefit that is prospective
only, since existing MIT releases stay forkable.

**Blanket permissive across the organization.** Rejected. It solves the
compliance problem by abandoning copyleft everywhere, including on
infrastructure and documentation where copyleft costs nothing and no
sourced-code ambiguity exists.

**Leave licensing unwritten.** Rejected. That is the current state, and it
produced a survey where six of eleven repositories disagree with an intent
nobody recorded, plus an audit finding no one could action.

**Per-repository judgment with no classes.** Rejected. It reproduces the
existing drift under a new name, and gives no answer at bootstrap time when the
decision actually gets made.

## References

- `decisions/0013-repository-settings-baseline.md`, the precedent for
  class-based baselines and the source of the "policy enforced by nothing"
  framing
- `decisions/0007-release-publication-flow.md`, whose classes describe
  publication rather than licensing and are deliberately not reused here
- `runbooks/new-repository.md`, whose licensing step is added in the same
  change; it previously said only "use the organization-approved license",
  pointing at a policy that did not exist
