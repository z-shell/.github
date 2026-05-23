---
name: project-wiki-prism
description: Prism syntax highlighting implementation for wiki — TypeScript grammar + CSS token palette
metadata: 
  node_type: memory
  type: project
  originSessionId: 4d49a48e-3672-4e20-a4d8-771b3a0317e2
---

The wiki (Docusaurus 3) has a custom Prism grammar for ZSH, Zi, and ZUnit code blocks.

**Key files:**
- `src/prism/z-shell-languages.ts` — exports `registerZShellLanguages(Prism)`, defines 3 languages
- `src/theme/prism-include-languages.ts` — swizzled Docusaurus loader, delegates to original then calls `registerZShellLanguages`
- `src/css/custom.css` — CSS variables `--site-zsh-builtin-color`, `--site-zi-command-color`, etc. with `:is(code[class*="language-zsh"], ...)` selectors

**Token map:** `zsh-builtin`→teal, `zsh-expansion-flag`→purple, `zsh-special-parameter`→amber, `zsh-glob-qualifier`→magenta, `zi-command`→gold (bold), `zi-ice`→teal-green, `zunit-command`→coral, `zunit-directive`→royal-blue, `zunit-assertion`→emerald.

**Why:** Prism's bash theme colors too many tokens identically — they "blend in". Named CSS variables override per-class colors for both light (GitHub) and dark (Dracula) themes.

**How to apply:** When editing syntax highlighting, use `insertBefore()` with named capture groups (ESLint `prefer-named-capture-group` is enforced — use `(?<lb>...)` not `(...)` for lookbehind groups).
