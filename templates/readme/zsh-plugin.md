<!--
Zsh Plugin README Template

Use this template for new Z-Shell Zsh plugins and substantial README
refactors. Replace every angle-bracketed field and remove instructional
comments before publication.

Required sections may be concise, but they must not be omitted. Optional
sections should be included only when they help users understand or operate the
plugin.

---
-->

<!-- markdownlint-disable MD033 -->

<div align="center">
  <a href="https://github.com/z-shell/<repository>">
    <img
      src="https://raw.githubusercontent.com/z-shell/zi/main/docs/images/logo.svg"
      alt="Z-Shell logo"
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
    <a href="LICENSE">
      <img
        src="https://img.shields.io/github/license/z-shell/<repository>"
        alt="License"
      />
    </a>
  </p>
</div>

## Features

- <Concrete capability>
- <Concrete capability>
- <Concrete capability>

<!-- Optional: include a screenshot or short demo only when it makes behavior
materially easier to understand. Use a repository-owned asset, useful alt text,
and restrained dimensions. Until Linear ZSH-18 lands, generated visuals are not
available and the asset must be reviewed manually when output changes.

![<Screenshot alt text describing the visible behavior>](<repository-owned-asset-path>)
-->

## Requirements

- Zsh <supported version or "a currently supported Zsh release">
- `<required-command>` available on `PATH`
- <platform or terminal constraint, if any>

## Installation

### Zi

```zsh
zi light z-shell/<repository>
```

<!-- Optional: retain one advanced Zi example only when it demonstrates a real
plugin capability, not merely an alternative spelling of the basic load. -->

### Other plugin managers

<List only intentionally supported or verified loading methods. Keep this
section compact and do not compare competing projects' feature sets. Remove
this subsection entirely when no additional manager has verified support.>

## Configuration

<State which values must be set before loading. Document only the public
contract.>

| Name               | Type     | Default     | Effect              |
| ------------------ | -------- | ----------- | ------------------- |
| `<public-setting>` | `<type>` | `<default>` | <Observable effect> |

## Usage

<Show the smallest useful example. Use a table for exact alias, command, or
option mappings.>

## Lifecycle and side effects

- <State changed during load>
- <Behavior when a required dependency is unavailable>
- <Unload function and the state it restores>

## Verification

From the repository root:

```bash
<exact verification command>
```

<State any prerequisite not supplied by the repository.>

## Documentation and support

- [Z-Shell wiki](https://wiki.zshell.dev/)
- [Report an issue](https://github.com/z-shell/<repository>/issues)

## Release model

<State the stable branch, development branch when applicable, and whether the
plugin is consumed directly from Git or published as a versioned artifact.>

## Contributing and license

Contributions follow the
[Z-Shell organization guidance](https://github.com/z-shell/.github).
This project is distributed under the terms in [LICENSE](LICENSE).

---

## Maintainer checklist

- [ ] The purpose and feature claims match current implementation behavior.
- [ ] Zi is the first installation path.
- [ ] Other manager examples are intentionally supported or verified.
- [ ] Public settings, aliases, functions, hooks, and defaults are complete.
- [ ] Load failures and unload behavior are documented.
- [ ] The verification command runs from a clean checkout.
- [ ] Long-form guidance links to the wiki instead of being duplicated.
- [ ] Badges are maintained signals rather than decoration.
- [ ] Images use useful alt text and durable repository-owned URLs.
- [ ] Screenshots or demos are included only when they explain behavior.
- [ ] Release-model and stable-branch statements match organization policy.
- [ ] No competitor comparison creates an avoidable drift obligation.

<!-- markdownlint-enable MD033 -->
