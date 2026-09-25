# 30. The zsh-lint Parser-Fork Trigger Has Fired: Fork the Syntax Package and Migrate Adapters by Family

- **Status:** PROPOSED
- **Date:** 2026-09-25
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0023](0023-zsh-lint-parser-front-end-strategy.md) point 4 lets `z-shell/zsh-lint` maintain a fork of the `mvdan.cc/sh/v3/syntax` package only when a trigger fires, one of which is that "the adapter chain becomes the bottleneck: a composition failure in the pairwise matrix that cannot be fixed inside one adapter, or an adapter count that makes the matrix impractical to keep green". When it fires, "the fork replaces adapters for the constructs it covers rather than adding to them".

The records in `z-shell/zsh-lint` now meet both halves of that condition.

- **Growth.** The adapter chain grew from 13 to 29 adapters between 2026-09-17 and 2026-09-25, and the non-test code in `internal/parse` from 6,910 to 13,735 lines. Two scanner functions exceed 450 lines each. The pairwise composition matrix has 812 ordered pairs, too many to enumerate in full orderings, so a sampled random-order test stands in for it.
- **Cost.** Every masked retry parses the whole file again. [zsh-lint#357](https://github.com/z-shell/zsh-lint/issues/357) measured 777 s for `z-shell/zi` `zi.zsh`; after [zsh-lint#365](https://github.com/z-shell/zsh-lint/pull/365) it still costs 829 whole-file parses at an adapter nesting depth of 57 ([zsh-lint#366](https://github.com/z-shell/zsh-lint/issues/366)), measured in CI since [zsh-lint#408](https://github.com/z-shell/zsh-lint/issues/408).
- **A defect class that lives in the adapters.** Each adapter finds its sites with its own byte scanner, and the scanners disagree about quoting: [zsh-lint#280](https://github.com/z-shell/zsh-lint/issues/280), [zsh-lint#393](https://github.com/z-shell/zsh-lint/issues/393), [zsh-lint#401](https://github.com/z-shell/zsh-lint/issues/401), and [zsh-lint#429](https://github.com/z-shell/zsh-lint/issues/429) are each a context one scanner misread. Shared helpers now cover part of it, and the probe grid of [zsh-lint#428](https://github.com/z-shell/zsh-lint/issues/428) keeps finding more ([zsh-lint#435](https://github.com/z-shell/zsh-lint/issues/435), [zsh-lint#439](https://github.com/z-shell/zsh-lint/issues/439), [zsh-lint#440](https://github.com/z-shell/zsh-lint/issues/440), [zsh-lint#441](https://github.com/z-shell/zsh-lint/issues/441)).
- **A composition failure one adapter cannot fix.** `zi.zsh` line 2910, `if [[ $1 = (load|light|snippet) ]] {`, is rejected on `main` because the alternate-if and nested-pattern adapters do not compose on it.

[zsh-lint#443](https://github.com/z-shell/zsh-lint/issues/443) measured the alternative instead of arguing it. The spike forked mvdan/sh v3.14.1 in-repo with a `go.mod` `replace` directive, so no import path changed and the unmodified fork passed every test, then implemented the brace-form `if`/`elif`/`else` and `while`/`until` family in the parser and removed the alternate-if adapter from the chain.

- The parser change is +136/-18 lines in `syntax/parser.go`, behind `LangZsh`, and upstream's own `syntax` test suite still passes.
- About 3,100 lines of adapter and test code become removable, and the composition matrix drops to 756 pairs.
- On a 598-file probe grid of the family, native Zsh as the oracle, known gaps drop from 57 to 13 and known false accepts from 25 to 0, with no regression. The family also parses inside `"$( )"`, where #280's scanner defect had rejected it, because no byte scanner is involved.
- Across the 340-file workspace and corpus, 339 verdicts are unchanged, and `zi.zsh` parses past line 2910.
- Seven native Zsh rules had to be found and encoded, three of them through the adapter's existing tests. The existing test suite and the probe grid were enough to find and check each one.

## Decision

1. **The trigger in ADR-0023 point 4 has fired.** `zsh-lint` maintains a fork of the `mvdan.cc/sh/v3` module, starting from the upstream release it pins.
2. **The fork lives in the repository.** It is kept under `third_party/mvdan-sh` with a `replace` directive in `go.mod`, retains the upstream BSD-3-Clause license (class L3 under [ADR-0017](0017-licensing-standard-by-provenance.md)), and carries only the packages `zsh-lint` builds. Local changes are confined to Zsh behaviour behind `LangZsh`, and upstream's own tests must keep passing on the fork.
3. **Adapters migrate by construct family.** Each family moves into the fork in its own pull request, which removes the adapter it replaces in the same change and proves parity: no verdict regression and no new false accept on the corpus, the workspace, and a probe grid of the family's valid and invalid variants judged by `zsh -f -n`, plus the remaining adapters' retry cost on the heaviest workspace files. The brace-form `if`/`while` family from #443 is the first.
4. **No new adapters.** A new parser gap is fixed in the fork, or in an existing adapter's shared scanner when it belongs to a family not yet migrated. An adapter is never added.
5. **Upstream stays a source of fixes.** An upstream release is taken by rebasing the fork's local patch onto it, under ADR-0023 point 3's tree-shape assertions. Offering a local change upstream stays optional, as in ADR-0023 point 2.

## Consequences

### Positive

- The largest source of parser defects, byte scanners reading quoting differently from the lexer, shrinks with each migrated family instead of growing with each fix.
- Retry cost and the composition matrix fall with each migration, because the fork parses in one pass what an adapter reached through whole-file retries.
- A gap that needs a new AST shape, which an adapter cannot express, has a place to be fixed.

### Negative

- Each upstream release now costs a rebase of the local patch. The patch is one file today, and it grows with each migrated family.
- Migration is real work per family. The spike shows the adapters' tests hold rules the native grammar must reproduce, so a family moves only when parity is shown, not by deleting its adapter.
- Until every family has moved, two mechanisms coexist, and a construct's behaviour depends on which one owns it.

### Neutral

- The survey corpus, the composition matrix for the adapters that remain, the probe grid, and the native oracle test stay the safety net ADR-0023 point 5 requires.
- ADR-0023 is refined, not superseded: its points 1 to 3 and 5 still hold.

## Alternatives considered

1. **Keep adding adapters.** Rejected: ADR-0023 point 4 excludes it once the trigger fires, and every measure above grows with each adapter.
2. **Migrate every family at once.** Rejected: a single large change cannot show parity family by family, and the spike's parity work shows each family needs its own evidence.
3. **Shared scanners only, no fork.** Rejected as the end state: shared helpers reduce the scanner defect class (#399, #436, #442) but keep whole-file retries, the composition matrix, and the adapters' size, and cannot add an AST shape. They remain the tool for families not yet migrated.
4. **An independent Zsh parser.** Rejected for the reason ADR-0023 gives: the analyzer and every rule consume mvdan/sh's typed tree, and the fork keeps that tree.

## References

- [ADR-0023](0023-zsh-lint-parser-front-end-strategy.md): the trigger this record finds fired.
- [zsh-lint#443](https://github.com/z-shell/zsh-lint/issues/443): the spike and its measurements; branch `feature-443`.
- [zsh-lint#366](https://github.com/z-shell/zsh-lint/issues/366), [zsh-lint#357](https://github.com/z-shell/zsh-lint/issues/357): retry cost.
- [zsh-lint#280](https://github.com/z-shell/zsh-lint/issues/280), [zsh-lint#393](https://github.com/z-shell/zsh-lint/issues/393), [zsh-lint#401](https://github.com/z-shell/zsh-lint/issues/401), [zsh-lint#429](https://github.com/z-shell/zsh-lint/issues/429): the scanner defect class.
- [zsh-lint#408](https://github.com/z-shell/zsh-lint/issues/408), [zsh-lint#412](https://github.com/z-shell/zsh-lint/issues/412), [zsh-lint#428](https://github.com/z-shell/zsh-lint/issues/428): the parse-count trace, verdict comparison, and probe grid used as evidence.
- [z-shell/.github#658](https://github.com/z-shell/.github/issues/658): the decision request.
- [ADR-0017](0017-licensing-standard-by-provenance.md): licensing class L3.
