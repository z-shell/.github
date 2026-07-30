# Patterns — z-shell

This file records implementation idioms already observed in multiple z-shell repositories. It exists to reduce drift, not to invent new style rules.

The canonical Zsh requirements live in
`.github/instructions/zsh-scripting.instructions.md`; machine-readable release,
profile, rule, and source-class metadata lives in
`lib/zsh-standard-policy.json`. Patterns below are observed examples, not a
second policy source. When an observed pattern conflicts with a required rule,
the canonical standard wins and the pattern must be corrected.

Admission rule:

- only record patterns already present in at least two real repositories
- prefer linking to the wiki or plugin standard when a deeper explanation already exists
- supersede patterns by updating this file, not by relying on private memory

## Plugin entry-point skeleton

Observed in:

- `z-shell/zsh-eza:zsh-eza.plugin.zsh`
- `z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh`
- `z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh`

Pattern:

1. Start `.zsh` entry files with the standard modeline.
2. Resolve `$0` via the `ZERO`-aware absolute-path pattern.
3. Keep path-sensitive initialization near the top of the file.

```zsh
# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et

0="${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
0="${${(M)0:#/*}:-$PWD/$0}"
```

Reference: <https://wiki.zshell.dev/community/zsh_plugin_standard#zero-handling>

Relevant canonical rules: `zsh/context/select-profile` and
`zsh/sourced/preserve-caller-state`.

## Register the repository directory in `Plugins`

Observed in:

- `z-shell/zsh-eza:zsh-eza.plugin.zsh`
- `z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh`
- `z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh`

Pattern:

```zsh
typeset -gA Plugins
Plugins[PLUGIN_KEY]="${0:h}"
```

Use a stable, repo-specific key and treat the registered directory as the root for cleanup and sibling-path resolution.

Reference: <https://wiki.zshell.dev/community/zsh_plugin_standard#standard-plugins-hash>

Relevant canonical rules: `zsh/plugin/document-global-state` and
`zsh/plugin/restore-state`.

## Guard `fpath` additions

Observed in:

- `z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh`
- `z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh`
- `z-shell/zsh-eza:zsh-eza.plugin.zsh`

Pattern:

- add `functions/` only when the plugin manager has not handled it and the
  exact literal path is absent
- when Zi's loader contract records handled `fpath` work through `PMSPEC`, the
  common Zi-aware form is:

```zsh
if [[ ${PMSPEC-} != *f* ]]; then
  fpath+=( "${0:h}/functions" )
fi
```

This loader-metadata guard does not independently inspect `fpath`.

- use an explicit literal membership guard under localized native option
  semantics when the entry point must tolerate non-Zi loader paths:

```zsh
() {
  builtin emulate -L zsh
  typeset -r functions_dir=$1

  if (( ${fpath[(Ie)${functions_dir}]} == 0 )); then
    fpath+=("$functions_dir")
  fi
} "${0:h}/functions"
```

Prefer the simpler form only when the repository relies on Zi's documented
loader contract.

Relevant canonical rules: `zsh/security/trust-paths` and
`zsh/plugin/restore-state`.

## Mandatory SHA-pinning for GitHub Actions

Observed in:

- `z-shell/zd:.github/workflows/`
- `z-shell/src:.github/workflows/`
- `z-shell/wiki:.github/workflows/`
- `z-shell/zunit:.github/workflows/`
- `z-shell/zi:.github/workflows/`

Pattern:

- Pin all external and internal GitHub Action references to a full 40-character commit SHA.
- Append a version or branch comment (e.g., `# v4` or `# main`) to the end of the line for human readability.

```yaml
# Good: pinned to SHA with version comment
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2

# Bad: mutable tag
uses: actions/checkout@v4
```

This ensures maximum security against tag-switching attacks and guarantees that CI runs are reproducible across time.

## Debian-based CI/Docker Environments

Observed in:

- `z-shell/zd:docker/Dockerfile`
- `z-shell/src:.github/workflows/`
- `z-shell/zunit:.github/workflows/`

Pattern:

- Prefer `debian:trixie-slim` (or current stable) or `ubuntu-latest` over Alpine Linux for CI/Docker environments.
- Ensure `glibc` compatibility and standard GNU userland tools (e.g., `apt-get`, `autoreconf`, `make`) are available to support consistent compilation and testing of Zsh and its modules.

This reduces toolchain fragmentation and prevents subtle bugs caused by `musl` libc differences when testing Zsh plugins that rely on compiled modules or specific system behaviors.

## AI Orchestration Placement

Observed in:

- `z-shell/.github:.github/agents/`
- `z-shell/wiki:.github/agents/`

Pattern:

- Place general-purpose engineering personas, global skills, and cross-repository instructions exclusively in the public `z-shell/.github` repository.
- Place domain-specific agents or instructions (e.g., Docusaurus documentation writers) directly in the repository where that specialized context applies (e.g., `wiki/`).
- Do not store AI boilerplate (agents, instructions, `.cursorrules`) in standard
  plugins. If a skill applies to more than one plugin, it belongs in the public
  `z-shell/.github` repository.
