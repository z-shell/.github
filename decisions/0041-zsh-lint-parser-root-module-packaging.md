# 41. Package the zsh-lint parser fork inside the root Go module

- **Status:** ACCEPTED
- **Date:** 2026-10-15
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0030](0030-zsh-lint-parser-fork-trigger-fired.md) selected an in-repository mvdan/sh fork so zsh-lint can fix proven Zsh parser gaps locally. Decision 2 places it under `third_party/mvdan-sh` with a local `replace` directive in `go.mod`. The directory and fork strategy remain useful, but that module arrangement prevents the documented versioned CLI installation: Go rejects the target module's replacement, and a nested module is omitted from the root module's downloadable zip.

[zsh-lint issue 653](https://github.com/z-shell/zsh-lint/issues/653) owns the install defect. Both `v1.4.0` and baseline commit `e9d1ea142518e4332999dc1da4ce17928bc04f3d` reproduce it with fresh caches. [Source PR 699](https://github.com/z-shell/zsh-lint/pull/699) retains the directory while making its packages part of the root module. Fresh-cache public installation from commit `f1c43fac9c8eadfc914a4af89a1beea11afca891` succeeds, and its parser and analyzer corpus results are unchanged. That unmerged implementation is evidence for this decision, not approval to merge or release it.

A separately published fork module could also make installation work, but would add an independent module version, release lifecycle and source-publication dependency solely for code retained with the CLI.

## Decision

Refine only the module-packaging clause of ADR-0030 decision 2:

1. Retain the parser fork under `third_party/mvdan-sh`, compiled as packages of the root `github.com/z-shell/zsh-lint` module. Imports between project and fork packages, and within the fork, use `github.com/z-shell/zsh-lint/third_party/mvdan-sh/...`. Do not ship a nested fork `go.mod` or `go.sum`, or require a local module replacement for the CLI's versioned installation. The root module must satisfy Go's versioned-install constraints without caller-local overrides.
2. Keep the upstream BSD-3-Clause license, copyright notices and provenance intact under [ADR-0017's L3 rule](0017-licensing-standard-by-provenance.md). Import normalization is a recorded local packaging change, not a relicense or grammar change.
3. Let the root module own dependencies and tools required by the retained fork packages and tests, including stringer. During an upstream refresh, follow `third_party/mvdan-sh/FORK.md`: copy retained packages without upstream module files, normalize imports, reapply documented local changes, review root dependency/tool resolution and regenerate with the root tools. Routine dependency updates remain under Renovate; parser-source refreshes remain deliberately reviewed changes.
4. Retain upstream tests and Zsh-only changes behind `LangZsh`. Root and fork-directory commands must resolve the same module. Preserve [ADR-0023](0023-zsh-lint-parser-front-end-strategy.md) and ADR-0030's tree-shape, native-oracle, corpus and adapter-removal gates. A module move is not evidence of a parser or lint-rule improvement.
5. Verify the downloadable module includes the parser and license, keep regressions for the module boundary and CLI dependency namespace, and prove fresh-cache versioned installation from the exact published implementation commit. Existing immutable tags remain unchanged. A fix reaches `@latest` only through the class-2 release boundary in [ADR-0007](0007-release-publication-flow.md).

ADR-0030 decisions 1 and 3 to 5 remain unchanged, as do decision 2's fork location and provenance requirements. Keep ADR-0030 as accepted history rather than silently rewriting its original packaging choice. Acceptance takes effect on main through the maintainer-approved ADR procedure; it does not merge an implementation, publish a release or advance consumer pins.

## Consequences

### Positive

- Versioned Go installation can obtain the CLI and its retained parser in one module download, without a separately published fork.
- Root module checks include the retained fork packages, and one dependency/tool selection governs both project and fork commands.
- The original fork strategy, upstream provenance and behavior gates remain intact.

### Costs and risks

- Upstream refreshes must normalize imports and merge required module/tool changes, so blindly copying an upstream tree is unsafe.
- Root dependency resolution applies to fork tests and generators; review selected versions and generated bodies rather than assuming equivalence with the former nested module.
- Formerly nested packages become visible to root checks. Preserve deliberate third-party lint boundaries explicitly while retaining build, vet and test coverage; do not mix inherited upstream lint cleanup into a packaging fix.
- Source-owned guidance must describe the target project's actual module layout. Approving and delivering a changed organization source to generated project consumers remains a separate revision-compatibility step.

## Alternatives considered

1. **Publish and version a separate fork module.** Technically viable, but adds a release and availability dependency not needed for this in-repository fork.
2. **Keep the replacement and document source-checkout installation only.** Avoids import migration but abandons the documented versioned Go installation contract instead of repairing it.
3. **Vendor or duplicate the parser elsewhere.** Adds another directory or ownership boundary without improving the existing retained fork's provenance and refresh workflow.

## References

- [Organization issue 795](https://github.com/z-shell/.github/issues/795), this scoped proposal and guidance correction.
- [Original fork decision request](https://github.com/z-shell/.github/issues/658) and [acceptance PR](https://github.com/z-shell/.github/pull/659).
- [Source implementation and verification](https://github.com/z-shell/zsh-lint/pull/699), including the public-commit install proof and inconclusive import-only mutation limits.
- [Fork packaging and refresh contract at the tested implementation](https://github.com/z-shell/zsh-lint/blob/f1c43fac9c8eadfc914a4af89a1beea11afca891/third_party/mvdan-sh/FORK.md).
- [ADR drafting and acceptance](../runbooks/adr.md).
