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

Status: retired. Do not copy the observed entry-point snippet. Assigning
special parameter `0` at sourced top level can replace caller state, and
deriving a reusable path from `${0:h}` after entering a function can select the
function name instead of the source file.

New work must follow
`.github/instructions/zsh-scripting.instructions.md` and start from
`.github/skills/new-zsh-plugin/templates/plugin.plugin.zsh`. No replacement is
published here because a safe replacement has not yet been observed in at least
two listed repositories.

Reference: <https://wiki.zshell.dev/community/zsh_plugin_standard#zero-handling>

Relevant canonical rules: `zsh/context/select-profile` and
`zsh/sourced/preserve-caller-state`.

## Register the repository directory in `Plugins`

Observed in:

- `z-shell/zsh-eza:zsh-eza.plugin.zsh`
- `z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh`
- `z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh`

Status: retired. Do not copy the observed unconditional `Plugins` assignment.
It overwrites caller state without preserving whether the key was absent or its
exact pre-load value, so an unload function cannot restore that state.

New work must follow
`.github/instructions/zsh-scripting.instructions.md` and use
`.github/skills/new-zsh-plugin/templates/plugin.plugin.zsh`. This catalog does
not publish a replacement until the complete snapshot and restoration shape is
observed in at least two listed repositories.

Reference: <https://wiki.zshell.dev/community/zsh_plugin_standard#standard-plugins-hash>

Relevant canonical rules: `zsh/plugin/no-shared-registry` and
`zsh/plugin/exact-lifecycle`.

## Guard `fpath` additions

Observed in:

- `z-shell/zsh-fancy-completions:zsh-fancy-completions.plugin.zsh`
- `z-shell/z-a-meta-plugins:z-a-meta-plugins.plugin.zsh`
- `z-shell/zsh-eza:zsh-eza.plugin.zsh`

Status: retired. Do not copy either observed `fpath` snippet. The Zi-aware
guard relies on loader metadata and does not independently inspect `fpath`;
both observed shapes also derive the directory from caller-sensitive `${0:h}`.
The localized literal-membership calculation alone does not make that path
derivation or lifecycle ownership safe.

New work must follow
`.github/instructions/zsh-scripting.instructions.md` and use
`.github/skills/new-zsh-plugin/templates/plugin.plugin.zsh`. This catalog does
not publish a replacement because the complete first-source ownership and
unload-restoration shape has not been observed in at least two listed
repositories.

Relevant canonical rules: `zsh/security/trust-paths` and
`zsh/plugin/exact-lifecycle`.

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
