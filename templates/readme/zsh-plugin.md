# Zsh Plugin README Template

Use this template for a maintained Z-Shell repository README and for a substantial README refactor. Plugins use it directly; annexes, tools, and modules adapt the same structure through the `create-readme` archetype guidance. A focused correction does not need it.

## How to use it

1. Copy everything between `<!-- TEMPLATE START -->` and `<!-- TEMPLATE END -->` into exactly one repository README: `docs/README.md` when `docs/` exists, otherwise `.github/README.md` when `.github/` exists, and otherwise `README.md` at the repository root.
2. Replace every `<angle-bracket>` placeholder with repository-specific content, including path placeholders such as `<license-path>`.
3. Update relative links for the chosen README location, such as `../LICENSE` from `docs/` or `.github/`.
4. Delete every `<!-- ... -->` comment. Comments are guidance for the author, never README content.
5. Drop a section marked optional when it would not help a user understand or operate the repository. A required section may be short, but it stays.
6. Work through the [maintainer checklist](#maintainer-checklist) before publishing.

## Section map

Sections run from what an evaluator needs first to what a contributor returns to later.

| Section                    | Status   | Question it answers                                     |
| :------------------------- | :------- | :------------------------------------------------------ |
| Header                     | Required | What is this, is it maintained, and under which license |
| Features                   | Required | Why would I want it                                     |
| Demo                       | Optional | What does it look like                                  |
| Requirements               | Required | Can I run it                                            |
| Installation               | Required | How do I get it, with Zi first                          |
| Usage                      | Required | What do I do after it loads                             |
| Configuration              | Required | How do I change its behavior                            |
| Lifecycle and side effects | Required | What does it touch in my shell, and how do I remove it  |
| Portable shell contract    | Required | Which names, files, and directories the plugin owns     |
| Verification               | Required | How do I check a checkout                               |
| Documentation and support  | Required | Where do I read more and report problems                |
| Release model              | Required | How does it ship                                        |
| Contributing and license   | Required | How do I help, and under which terms                    |

## Styling conventions

- The header is a centered HTML block: logo, title, one-sentence tagline, and a badge row of maintained signals only.
- Secondary plugin managers live in `<details>` blocks so Zi stays the visible path.
- GitHub alerts carry operational notes: `[!NOTE]` for compatibility floors and optional dependencies, `[!TIP]` for optional optimizations, `[!IMPORTANT]` for mandatory prerequisites and breaking configuration changes, `[!WARNING]` for terminal constraints and known conflicts. Use at most one per section, keep the marker and body on separate quoted lines, and rely on Prettier's default Markdown `preserve` behavior so formatting does not collapse the alert into plain blockquote text.
- Reference data (styles, aliases, commands) goes in a table with explicit column alignment, surrounded by blank lines.
- Code blocks carry a language tag (`zsh`, `bash`, `console`).
- Prose is one paragraph per line with no hard wrapping.

<!-- TEMPLATE START -->

<!-- Put this content in exactly one repository README: `docs/README.md` when `docs/` exists, otherwise `.github/README.md` when `.github/` exists, and otherwise `README.md` at the repository root. Keep a single repository README and adjust relative links such as `<license-path>` for the chosen location, for example `../LICENSE` from `docs/` or `.github/`. -->

<div align="center">
  <a href="https://github.com/z-shell/<repository>">
    <img
      src="https://raw.githubusercontent.com/z-shell/zi/main/docs/images/logo.svg"
      alt="<Plugin name> logo"
      width="72"
      height="72"
    />
  </a>

  <h1>&lt;Plugin name&gt;</h1>
  <p>&lt;One sentence describing the observable value of the plugin.&gt;</p>
  <p>
    <a href="https://github.com/z-shell/<repository>/actions/workflows/<validation-workflow>.yml">
      <img
        src="https://github.com/z-shell/<repository>/actions/workflows/<validation-workflow>.yml/badge.svg?branch=main"
        alt="CI status"
      />
    </a>
    <a href="<license-path>">
      <img
        src="https://img.shields.io/github/license/z-shell/<repository>"
        alt="License"
      />
    </a>
  </p>
</div>

## Features

<!-- Three to six bullets. Each names an observable capability, not an implementation detail. -->

- <Concrete capability>
- <Concrete capability>
- <Concrete capability>

## Demo

<!-- Optional: keep the image only when it makes behavior materially easier to understand. Use a repository-owned asset, descriptive alt text, and restrained dimensions. Review the asset by hand whenever output changes; reusable demo generation is tracked in z-shell/.github#458. -->

![<What the visual demonstrates>](repository-owned-asset-path)

## Requirements

- Zsh <supported version or "a currently supported Zsh release">
- `<required-command>` available on `PATH`
- <Platform or terminal constraint, if any>

## Installation

### Zi

```zsh
zi light z-shell/<repository>
```

<!-- Optional: keep one advanced Zi example only when it demonstrates a real plugin capability, not an alternative spelling of the basic load. -->

### Other plugin managers

<!-- List only intentionally supported or verified loading methods, one collapsible block per manager. Do not compare competing projects. Present manager-specific APIs as optional profiles, never as portable requirements. -->

The plugin follows the [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard) and can be sourced by other Zsh plugin managers.

<details>
<summary>&lt;Manager name&gt;</summary>

```zsh
<manager-specific load command>
```

</details>

## Usage

<!-- Show the smallest useful example first. Use the table for exact alias, command, or option mappings; delete it when there is nothing to map. -->

```zsh
<smallest useful example>
```

| Alias or command | Effective command      | Purpose             |
| :--------------- | :--------------------- | :------------------ |
| `<name>`         | `<what it expands to>` | <Observable effect> |

## Configuration

<!-- Document the one namespaced zstyle context. Do not expose scattered global parameters or environment variables as parallel settings. -->

Set styles in the `:<portable_ascii_identifier>:config` context before the plugin loads.

| Style              | Type     | Default     | Effect              |
| :----------------- | :------- | :---------- | :------------------ |
| `<style-property>` | `<type>` | `<default>` | <Observable effect> |

<!-- Optional: keep the alert only for a breaking configuration change, such as a removed global parameter, and name the replacement. -->

> [!IMPORTANT]
> <Removed setting> was removed. Replace it with the `<style-property>` style above.

## Lifecycle and side effects

- <State changed during load>
- <Namespacing and option-scoping behavior>
- <Behavior when a required dependency is unavailable>
- <Unload function and the state it restores>
- <Confirm that load performs no network activity>

## Portable shell contract

| Item                         | Value                                                                    |
| :--------------------------- | :----------------------------------------------------------------------- |
| Project identifier           | `<portable_ascii_identifier>`                                            |
| Authoritative entrypoint     | `<repository>.plugin.zsh`                                                |
| Public configuration context | `:<portable_ascii_identifier>:config`                                    |
| Public functions             | `<identifier_function>`                                                  |
| Unload function              | `<portable_ascii_identifier>_plugin_unload`                              |
| Optional directories         | <Only the `lib/`, `functions/`, `completions/`, and `bin/` roles in use> |

## Verification

From the repository root:

```bash
<exact verification command>
```

<State any prerequisite not supplied by the repository.>

## Documentation and support

- [Z-Shell wiki](https://wiki.zshell.dev/)
- [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
- [Zsh documentation](https://zsh.sourceforge.io/Doc/)
- [Zi plugin manager](https://github.com/z-shell/zi)
- [Report an issue](https://github.com/z-shell/<repository>/issues)

## Release model

<State that contributions integrate on `main` and whether the plugin is consumed directly from Git or published as a versioned artifact. A persistent integration branch requires an accepted organization ADR naming the repository.>

## Contributing and license

Contributions follow the [Z-Shell organization guidance](https://github.com/z-shell/.github). This project is distributed under the terms in [LICENSE](<license-path>).

---

<div align="center">
  <p>Developed with ❤️ by the <a href="https://github.com/z-shell">Z-Shell Community</a>.</p>
</div>

<!-- TEMPLATE END -->

## Maintainer checklist

Accuracy:

- [ ] The purpose and feature claims match current implementation behavior.
- [ ] Public settings, aliases, functions, hooks, and defaults are complete.
- [ ] Load failures, partial cleanup, and ownership-aware unload behavior are documented.
- [ ] The verification command runs from a clean checkout.

Installation paths:

- [ ] Zi is the first installation path.
- [ ] Other manager examples are intentionally supported or verified.
- [ ] Manager-specific profiles are distinguished from portable requirements.
- [ ] No competitor comparison creates an avoidable drift obligation.

Plugin Standard:

- [ ] One portable ASCII identifier owns every persistent shell-visible name.
- [ ] Ordinary public configuration uses one namespaced `zstyle` context.
- [ ] Portable code neither requires nor mutates a shared plugin registry.
- [ ] Plugin-owned state is namespaced, option changes are scoped, and unload reverses every owned side effect.
- [ ] Plugin load performs no network activity.

Presentation:

- [ ] Every placeholder is replaced and every template comment is deleted.
- [ ] Badges are maintained signals rather than decoration.
- [ ] Images use useful alt text and durable repository-owned URLs.
- [ ] Screenshots or demos are included only when they explain behavior.
- [ ] Long-form guidance links to the wiki instead of being duplicated.

Policy:

- [ ] Release-model and stable-branch statements match organization policy.
