# 23. zsh-lint Tracks Upstream, Fixes Locally, and Forks the Parser on a Trigger

- **Status:** ACCEPTED
- **Date:** 2026-09-15
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

`zsh-lint` parses Zsh with the `mvdan.cc/sh/v3/syntax` front end in its Zsh
dialect (`LangZsh`, since v3.13.0). The project's recorded parser strategy is
upstream-first: map every parser gap to an open `mvdan/sh` issue, prefer
tracking and contributing upstream over local preprocessing, and bump on
release (`zsh-lint` `docs/project/2026-06-12-langzsh-switch.md`,
`docs/project/2026-06-12-frontend-comparison.md`, and the body of
[zsh-lint#125](https://github.com/z-shell/zsh-lint/issues/125)).

Practice has moved away from that text without a recorded decision:

- Eleven local compatibility adapters ship in `internal/parse`, registered in
  `adapter_chain.go`. Every gap closed since #125 (#112, #120, #123, #125,
  #163, #202, #205) was closed locally.
- The upstream maintainer declared initial Zsh support done on 2026-06-02 and
  asked for issues to be filed and voted under the `zsh` label. The issue that
  covers the inline loop family, [mvdan/sh#1203](https://github.com/mvdan/sh/issues/1203),
  has had no maintainer response since 2025-10-15.
- The upstream AST cannot express every Zsh construct. `repeat` has no node at
  all, so `repeat 3; print hi` parses silently as two commands
  ([zsh-lint#208](https://github.com/z-shell/zsh-lint/issues/208)). A
  source-rewriting adapter cannot fix that; only a parser change can.
- Each adapter rewrites source and re-parses, and adapters compose pairwise.
  `adapter_chain.go` records that 40 of 42 ordered adapter pairs once failed
  before the chain was introduced. The composition matrix grows with every
  adapter.
- Upstream releases still carry fixes worth taking. v3.14.1 parses
  `${a[(R)$p/*]}` correctly ([zsh-lint#209](https://github.com/z-shell/zsh-lint/issues/209))
  but turns `foreach ... end` from a parse error into a silent three-command
  misparse ([zsh-lint#214](https://github.com/z-shell/zsh-lint/issues/214)),
  so a bump is a behavior change that needs tree-shape tests, not a routine
  version update.

The maintainer's concern, raised while reviewing
[zsh-lint#206](https://github.com/z-shell/zsh-lint/issues/206), is that
building the roadmap on upstream responsiveness leaves `zsh-lint` exposed if
upstream stalls. The risk is not that a pinned Go module stops working; a
pinned pure-Go dependency cannot break under the project. The risk is
stagnation: gaps that only a parser change can close, accumulating in a layer
that was designed as an exception.

`mvdan/sh` is BSD-3-Clause. Under
`decisions/0017-licensing-standard-by-provenance.md` class L3, a fork retains
the upstream license and is compatible with `zsh-lint`'s GPL-3.0.

## Decision

`zsh-lint` owns its parser coverage. Upstream is a source of fixes to be taken
and tested, not a dependency to wait on.

1. **Fix locally by default.** A proven valid-Zsh gap with corpus evidence is
   fixed in `zsh-lint`, under the existing adapter contract in
   `docs/project/parser-gap-workflow.md`, without waiting for or conditioning
   on an upstream response. Gaps without corpus evidence are tracked and
   prioritized by evidence, not by upstream status.
   A construct that parses successfully with the wrong shape is a gap of the
   same class and must not reach analysis silently: the front end rejects it
   with a positioned parse error until it is supported (the reserved-word
   guard for `repeat` and `foreach` in
   [zsh-lint#217](https://github.com/z-shell/zsh-lint/pull/217)), or carries
   it as typed `parse.File` metadata. Neither requires a fork; a fork is
   needed only when a correct typed tree is required and metadata cannot
   carry it (point 4).
2. **Track upstream; filing is optional.** Where an upstream issue already
   exists, link it as a reference. Filing new upstream issues is at the
   maintainers' discretion and is never a prerequisite for local work.
   Upstream status does not appear in acceptance criteria.
3. **Take upstream releases as tested fixes.** Bump the pinned front end when a
   release closes a tracked gap. A bump is a parser behavior change: it lands
   with tree-shape assertions for every corpus fixture the release affects,
   and the survey corpus runs before and after. A fixture that stops erroring
   must fail on tree shape rather than pass vacuously. The assertions are
   adoption gates: a bump whose affected assertion fails does not merge until
   the front end fails closed on that construct or produces the correct tree.
   v3.14.1 is the reference case: it fixes #209 and turns `foreach ... end`
   into a successful three-command misparse, so it ships only with the guard
   from point 1.
4. **Fork the parser on a trigger, not in advance.** Maintain a fork of the
   `syntax` package (class L3, upstream license retained) only when one of
   these holds:
   - a tracked gap needs an AST node the upstream tree does not have and the
     `parse.File` metadata exception in the parser-gap workflow cannot carry
     it faithfully, or
   - the adapter chain becomes the bottleneck: a composition failure in the
     pairwise matrix that cannot be fixed inside one adapter, or an adapter
     count that makes the matrix impractical to keep green.
     Until a trigger fires, the fork is not created. When it fires, the fork
     replaces adapters for the constructs it covers rather than adding to them.
5. **Keep the safety net.** The `gap-*` / `ok-*` survey corpus, the adapter
   composition matrix, and tree-shape assertions are the mechanism that makes
   a bump or a fork testable. They are maintained as product code.

## Consequences

- Contributors no longer read "upstream-first" and stall once the companion
  change [zsh-lint#219](https://github.com/z-shell/zsh-lint/pull/219) lands:
  it states the local-first rule in the workflow document, links this record,
  and marks the upstream-first wording in the 2026-06-12 records as
  superseded. Until it merges, those records still say upstream-first and
  this record governs.
- Adapter growth continues in the short term. The trigger in point 4 bounds
  it: the first construct that an adapter cannot express correctly moves the
  work to a fork instead of a wider adapter.
- Bumps cost more than a version edit because they require tree assertions.
  In exchange, a bump can no longer turn a loud error into a silent false
  negative unnoticed.
- A fork, once created, carries merge-tracking cost against upstream. That
  cost is paid only after a trigger proves it is cheaper than the alternative.
- Upstream issues that already exist remain useful references; `zsh-lint`
  neither depends on nor promises them.

## Alternatives considered

- **Keep upstream-first as written.** Rejected: practice has already diverged,
  the upstream maintainer has declared the initial work done, and `repeat`
  shows a gap that upstream-first cannot close without upstream action.
- **Fork now.** Rejected: no current gap requires a parser change that the
  metadata exception cannot carry, so a fork today is merge-tracking cost with
  no benefit. The trigger keeps the option live.
- **Write an independent Zsh parser.** Rejected: the 2026-06-12 front-end
  comparison found `mvdan/sh` ahead of the alternatives on the corpus, and the
  analyzer and every rule consume its typed AST.
- **Stop bumping the front end to avoid behavior drift.** Rejected: pinning
  forever forgoes fixes already written, and the tree-shape requirement
  addresses the drift.
- **Adopt tree-sitter-zsh.** Rejected in the 2026-06-12 comparison; remains
  tracking-only under the same re-evaluation trigger.

## References

- [zsh-lint#206](https://github.com/z-shell/zsh-lint/issues/206): the review
  that surfaced the drift
- [zsh-lint#208](https://github.com/z-shell/zsh-lint/issues/208),
  [zsh-lint#209](https://github.com/z-shell/zsh-lint/issues/209),
  [zsh-lint#214](https://github.com/z-shell/zsh-lint/issues/214)
- [zsh-lint#125](https://github.com/z-shell/zsh-lint/issues/125): the
  upstream-first wording this replaces
- `zsh-lint` `docs/project/parser-gap-workflow.md`,
  `docs/project/2026-06-12-langzsh-switch.md`,
  `docs/project/2026-06-12-frontend-comparison.md`
- [mvdan/sh#120](https://github.com/mvdan/sh/issues/120): upstream Zsh
  support umbrella; [mvdan/sh#1203](https://github.com/mvdan/sh/issues/1203)
- `decisions/0011-zsh-lint-semantic-analyzer-architecture.md`
- `decisions/0017-licensing-standard-by-provenance.md`
