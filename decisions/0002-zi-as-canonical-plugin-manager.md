# 2. `zi` is the canonical plugin manager for the z-shell ecosystem

- **Status:** ACCEPTED
- **Date:** 2026-05-29
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

The z-shell organization contains several kinds of repositories:

- `zi` itself
- annexes that extend `zi`
- plugins that are commonly loaded through `zi`
- modules and shell libraries
- documentation and org-infrastructure repositories

This relationship is already visible in code, examples, naming, and maintenance practice, but it has not been stated clearly in a durable decision record.

That ambiguity hurts:

- contributor onboarding
- documentation consistency
- LLM-assisted maintenance
- breaking-change coordination when `zi` changes behavior

## Decision

`zi` is the canonical plugin manager for the z-shell ecosystem.

Specifically:

1. **Annexes** target `zi` directly and may depend on `zi` internals.
2. **Plugins** should remain plugin-manager-agnostic where practical, but `zi` is the reference manager for examples, testing, and documentation.
3. **Cross-manager compatibility** is welcome when it does not compromise `zi`-first behavior.
4. **Breaking changes in `zi`** must be reviewed against in-org consumers before release.
5. **Org documentation** should lead with `zi` examples unless a document is explicitly about cross-manager comparison.

## Consequences

### Positive

- Clear answer to "which plugin manager should I assume?"
- Annexes can rely on `zi` intentionally rather than implicitly
- Cross-repo change analysis becomes more tractable
- Default docs and examples become consistent

### Negative / costs

- Some users of other plugin managers may see the org as more opinionated.
- The ecosystem becomes more tightly coupled to `zi` as the load-bearing center.

### Neutral

- This does not require removing cross-manager support from compatible plugins.
- This ADR documents an existing reality more than it changes behavior.

## Alternatives considered

1. **No preferred plugin manager:** rejected because it diffuses maintenance and testing effort.
2. **Multiple co-equal canonical managers:** rejected because the org does not maintain a second equivalent center.
3. **Leave it implicit:** rejected because the ambiguity is the problem.

## References

- `https://github.com/z-shell/zi`
- `AGENTS.md`
