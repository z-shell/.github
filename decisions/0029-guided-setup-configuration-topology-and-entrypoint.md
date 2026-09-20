# 29. Guided Setup Configuration Topology and Startup Entrypoint

- **Status:** ACCEPTED
- **Date:** 2026-09-20
- **Deciders:** ss-o
- **Supersedes:** Configuration topology and startup integration in `decisions/0025-guided-setup-planner-first.md`
- **Superseded by:** None

## Context

[ADR-0025](0025-guided-setup-planner-first.md) established guided setup as a headless planner and applier first, implemented in `z-shell/src`, deferring a terminal interface until adoption proves the interface is a bottleneck. In ADR-0025, the planned configuration topology under the resolved configuration home (`$XDG_CONFIG_HOME/zi` when `XDG_CONFIG_HOME` is set and absolute, otherwise `$HOME/.config/zi`) consisted of three targets: `init.zsh`, `setup/pre.zsh`, and `setup/shell.zsh`. Under that original design, the startup integration block placed directly into `${ZDOTDIR:-$HOME}/.zshrc` was an inline guarded shell snippet that performed path resolution, declared `typeset -gA ZI`, chained `source setup/pre.zsh && source init.zsh && zzinit`, sourced `setup/shell.zsh` if successful, and printed diagnostics on failure.

During implementation in [z-shell/src#208](https://github.com/z-shell/src/issues/208) and delivery in [`z-shell/src` PR 221](https://github.com/z-shell/src/pull/221) (coordinated with [z-shell/.github#640](https://github.com/z-shell/.github/issues/640) and [`z-shell/.github` PR 649](https://github.com/z-shell/.github/pull/649)), this startup and configuration topology was refined. Placing multiline orchestration, fallback path checks, and error handling directly in user dotfiles cluttered `.zshrc`, made user dotfiles less readable, and coupled internal startup sequencing to external dotfile content. Any adjustment to initialization order or diagnostics would require modifying the user's `.zshrc`.

Additionally, the distribution contract for `public/sh/install.sh` needed to preserve its standalone nature while safely delegating to the planner. A clear contract was also required for companion asset retrieval, checksum verification, profile defaults, and documentation hierarchy across organization repositories.

## Decision

1. **Configuration targets.** Guided setup manages four dedicated targets under the resolved configuration home (`$XDG_CONFIG_HOME/zi` when `XDG_CONFIG_HOME` is set and absolute, otherwise `$HOME/.config/zi`):
   - `init.zsh`: The Zi loader asset, placed from bundled installer assets or retrieved from the selected `ZI_SRC_REF` (a branch, tag, or commit) and verified against `public/checksum.txt` from that same ref.
   - `setup/pre.zsh`: Sourced before `init.zsh`; contains pre-initialization configuration, explicit paths (`ZI[HOME_DIR]`, `ZI[BIN_DIR]`), stream selection (`ZI[STREAM]`), and pre-loader settings (`ZI[LOADER_HISTORY]`).
   - `setup/shell.zsh`: Sourced after `zzinit` completes; contains post-initialization shell configuration, including plugin recipes from meta-plugins capability bundles.
   - `setup.zsh`: The generated top-level startup entrypoint in the configuration home. It encapsulates startup sequencing, declares `typeset -gA ZI`, chains `setup/pre.zsh`, `init.zsh`, and `zzinit`, sources `setup/shell.zsh` on success, and prints structured diagnostics (`Zi setup: <step> failed`) naming the exact failed step if any stage fails.

2. **Short managed dotfile integration.** `${ZDOTDIR:-$HOME}/.zshrc` contains only a marker-delimited short block with one absolute, single-quoted source line targeting `setup.zsh`:

   ```zsh
   # >>> zi setup >>>
   source '/absolute/path/to/config/zi/setup.zsh'
   # <<< zi setup <<<
   ```

   The short block was chosen so that user dotfiles stay readable, minimal, and stable. Implementation details, internal path resolution, error handling, and sequencing logic live in the generated `setup.zsh` entrypoint rather than cluttering user dotfiles.

3. **Standalone installer and companion asset retrieval.** `install.sh` remains the public entrypoint and defaults to the `loader` profile. When invoked, `install.sh` retrieves its companion setup assets (`sh/setup.sh`, `zsh/init.zsh`, and `setup/profiles.tsv`, plus `sh/install_zpmod.sh` if `-a zpmod` is requested) from the selected `ZI_SRC_REF` (a branch, tag, or commit, defaulting to `main`), verifies them against the matching SHA-256 checksum manifest (`public/checksum.txt`) from that same selected ref, and then delegates `plan` and `apply` execution to `setup.sh`.

4. **Canonical documentation hierarchy and coordination.** Long-form user installation guidance is canonical in `z-shell/wiki` (`docs/getting_started/01_installation.mdx`). Public contract changes must coordinate across six surfaces:
   - the canonical wiki installation page (`z-shell/wiki`),
   - the canonical `zi-install` skill (`z-shell/.github` `.github/skills/zi-install/SKILL.md`),
   - delivered pinned skills in consumer repositories,
   - the `z-shell/zi` README,
   - the `z-shell/src` README (`docs/README.md`), and
   - the `z-shell/src` landing page (`public/index.html`).

## Consequences

### Positive

- User dotfiles (`.zshrc`) remain uncluttered, containing only a clean 3-line managed block.
- Startup sequencing, diagnostics, and error reporting live entirely within the generated `setup.zsh` entrypoint, allowing internal setup changes without altering `.zshrc`.
- `install.sh` remains a self-contained public entrypoint for `curl | sh` users while verifying companion assets against their SHA-256 checksums from the selected ref before delegating to `setup.sh`.
- The division of documentation responsibility is clear: `z-shell/wiki` holds canonical user guidance, while repository documentation remains focused on local implementation and architecture.

### Costs and risks

- Sourcing `setup.zsh` introduces an extra file in the configuration home and one additional indirection during startup, though performance overhead in Zsh is negligible.
- Changes to the public installation contract require coordinated updates across six distinct surfaces to prevent drift.

## Alternatives considered

- **Retain the multiline guarded block in `.zshrc` (ADR-0025 original design).** Rejected: embedding startup checks and error-handling chains directly in `.zshrc` clutters user dotfiles and makes subsequent maintenance invasive.
- **Bundle all setup assets into a single monolithic script.** Rejected: keeping `install.sh`, `setup.sh`, `init.zsh`, and `profiles.tsv` distinct maintains separation of concerns, testability, and standalone reuse.
- **Treat repository READMEs as canonical installation documentation.** Rejected: per [ADR-0006](0006-wiki-content-root-boundaries.md) and `AGENTS.md`, `z-shell/wiki` is the canonical source of truth for long-form user documentation.

## References

- [ADR-0025](0025-guided-setup-planner-first.md): Zi Guided Setup Is a Planner First
- [z-shell/src#208](https://github.com/z-shell/src/issues/208): Guided setup planner implementation
- [`z-shell/src` PR 221](https://github.com/z-shell/src/pull/221): Guided setup planner and companion assets
- [z-shell/.github#640](https://github.com/z-shell/.github/issues/640): Instruction routing for guided setup planner
- [`z-shell/.github` PR 649](https://github.com/z-shell/.github/pull/649): Initial routing for ADR-0025
- `z-shell/src` `public/sh/install.sh`, `public/sh/setup.sh`, `public/zsh/init.zsh`, `docs/README.md`
- `z-shell/wiki` `docs/getting_started/01_installation.mdx`
- [ADR-0002](0002-zi-as-canonical-plugin-manager.md)
- [ADR-0006](0006-wiki-content-root-boundaries.md)
- `AGENTS.md`
