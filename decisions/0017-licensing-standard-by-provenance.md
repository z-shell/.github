# 17. Licensing Standard by Provenance and Consumption

- **Status:** PROPOSED
- **Date:** 2026-08-18
- **Deciders:** TBD
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

**Class L2: organization-authored, loaded into a user's shell process.**
Plugin managers, plugins, annexes, and shell modules. **Permissive (MIT) by
deliberate choice.** The derivative-work boundary for sourced shell code is
unsettled, and the organization's own ecosystem depends on third parties
loading this code alongside their own.

**Class L3: third-party forks and repackaging.** **Upstream license retained,
never relicensed.** The organization does not hold the copyright.

### Assignments

| Repository              | Class | License | Action                       |
| ----------------------- | ----- | ------- | ---------------------------- |
| `.github`               | L1    | GPL-3   | compliant                    |
| `wiki`                  | L1    | GPL-3   | compliant                    |
| `z-a-meta-plugins`      | L2    | GPL-3   | see open question 1          |
| `zsh-fancy-completions` | L2    | GPL-3   | see open question 1          |
| `zi`                    | L2    | MIT     | compliant, deliberately      |
| `zunit`                 | L3    | MIT     | compliant, upstream retained |
| `zsh`                   | L3    | MIT     | compliant, upstream retained |
| `src`                   | ?     | GPL-3   | see open question 2          |
| `zd`                    | L1    | MIT     | relicense to GPL-3           |
| `zsh-lint`              | L1    | MIT     | relicense to GPL-3           |
| `zsh-eza`               | L2    | MIT     | compliant                    |

Every repository records its class, so a license becomes a deliberate recorded
choice rather than whatever the bootstrapping session happened to pick.

### Open questions for the accepting maintainer

1. `z-a-meta-plugins` and `zsh-fancy-completions` are L2 by consumption model
   but already carry GPL-3. Relicensing toward permissive would require the
   same contributor analysis in reverse and is not proposed here. Either accept
   them as documented L2 exceptions, or reclassify plugins as L1 and require
   `zi` and `zsh-eza` to move to GPL-3 instead.
2. `src` is the compiled Zsh module. It is loaded into the shell like L2, but
   is a compiled artifact rather than sourced script, and already carries
   GPL-3. It needs an explicit class rather than an inferred one.
3. `zd` and `zsh-lint` are the only two this ADR proposes actively changing.
   Both are organization-authored with no third-party copyright barrier.

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
- `runbooks/new-repository.md`, which needs a licensing step once this is
  accepted
