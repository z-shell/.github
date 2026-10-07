---
name: create-readme
description: "Create or refactor a repository README with polished GFM styling, valuable links, and high-clarity structure"
---

# Create README

Create an accurate, visually polished, and technically rigorous repository landing page using GitHub Flavored Markdown (GFM).

## Core Objectives

1. **Immediate Clarity:** Communicate the project's purpose and observable value within the first viewport.
2. **Visual Polish without Bloat:** Use clean typography, centered hero headers, uniform badge rows, and native GFM callouts.
3. **Frictionless Onboarding:** Lead with a concise quick-start path for the repository archetype, followed by short usage examples.
4. **Technical Depth via Disclosure:** Keep advanced configuration and troubleshooting inside collapsible `<details>` blocks; include secondary plugin managers there only for plugin-shaped repositories that support them.
5. **Canon Anchoring:** Link directly to the Z-Shell Wiki and authoritative documentation for the archetype. Use official Zsh manual sections for Zsh-facing repositories, and include plugin-standard and manager links only for plugin-shaped repositories.

---

## Required Workflow

1. Read the repository's source, tests, workflows, local instructions, release model, and linked organization policy before drafting.
2. Place exactly one repository README at `docs/README.md` when `docs/` exists, otherwise at `.github/README.md` when `.github/` exists, and otherwise at `README.md` in the repository root. Update relative links for the chosen location, such as `../LICENSE` from `docs/` or `.github/`.
3. Classify the repository archetype and start from the canonical [`knowledge/domains/documentation/templates/zsh-plugin.md`](https://github.com/z-shell/.github/blob/main/knowledge/domains/documentation/templates/zsh-plugin.md) in `z-shell/.github`. Prefer that file in the available organization checkout; otherwise read the linked source. Resolve it from the organization repository root, since a delivered skill may live elsewhere. Adapt the structure by archetype:
   - **Zsh Plugins (`zsh-*`):** Follow the [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard). Document namespaced `zstyle` contexts and clean `<plugin>_plugin_unload` routines.
   - **Zi Annexes (`z-a-*`):** Keep Zi as the installation path, adapt the Lifecycle and Zi integration sections to document registered ice modifiers, annex hooks (`before_load`, `after_load`), owned state parameters, and the unload function, and keep Portable shell contract content limited to manager-independent behavior.
   - **Compiled Modules:** Adapt plugin-specific sections into module-specific build toolchain, supported Zsh/platform matrix, loader and install path, verification, and release artifact policy.
   - **Plugin Managers (Zi):** Show requirements, installation, and the first useful shell configuration. Link to command, configuration, lifecycle, and installer integration references instead of imposing a plugin's portable contract on the manager.
   - **Go / CLI Tools (`zsh-lint`):** Adapt plugin-specific sections into tool-specific installation, binary distribution, CLI flags, verification, and generated API reference coverage.
   - **Environment / Meta (`zd`, `wiki`):** Adapt plugin-specific sections into environment-specific targets, local preview or container workflows, verification steps, and configuration mounts.
4. Verify every feature, setting, default, alias, lifecycle claim, command, and branch statement against the current implementation.
5. For Zsh plugins and Zi annexes, lead installation guidance with Zi. Keep other manager examples concise and place them inside collapsible `<details>` disclosure blocks.
6. Keep long-form ecosystem guidance in the wiki and link to it.
7. Preserve meaningful visual identity: a clear header, a restrained maintained badge set, accessible alt text, and an optional behavior-focused screenshot or demo.
8. Do not add competitor comparisons unless comparison is the document's explicit purpose.
9. Run repository-appropriate Markdownlint, link, syntax, and behavior checks before claiming completion.
10. Review a GitHub-compatible preview at desktop and about 375 CSS pixels wide. Check table readability, alert rendering, heading navigation, and the path from installation to first use. Record the preview method and any rendering limits; lint alone is not visual verification.

Required template categories are coverage requirements, not a demand for full sections on the landing page. Link to maintained references for detailed contracts and contributor procedures. Keep prerequisites, basic setup, and safety-critical warnings visible.

---

## Visual Design and GFM Standards

### 1. Hero Header Block

Use a centered HTML block for brand identity and status:

- Centered organization or repository logo (72x72 SVG).
- Large title and a concise tagline explaining observable value.
- Curated, uniform badge stack (flat-square style): applicable CI workflow status, release version, and license signals. Add Zsh Plugin Standard v2 compliance only for plugin-shaped repositories that actually comply.

### 2. GitHub Callout Alerts

Highlight operational details with native GFM alerts:

Put the marker on its own quoted line and the body on the next. Keep alerts outside HTML containers and nested elements, and verify that the repository formatter preserves the boundary:

```markdown
> [!NOTE]
> Set configuration before loading the plugin.
```

- `> [!TIP]` for performance optimizations (e.g. `wait lucid` turbo mode).
- `> [!NOTE]` for compatibility floors or optional dependencies.
- `> [!IMPORTANT]` for mandatory prerequisites or breaking configuration changes.
- `> [!WARNING]` for terminal constraints or known conflicts.

### 3. Collapsible Disclosures

Use `<details><summary>...</summary></details>` for:

- Secondary plugin manager recipes for plugin-shaped repositories that intentionally support them.
- Advanced configuration, including `zstyle` options or specialized ice modifiers when the archetype uses them.
- Migration notes from legacy or predecessor plugins.
- Troubleshooting guides and edge-case workarounds.

### 4. Compact Tables

All tables must comply with Markdownlint MD058 and MD060:

- Surround every table with blank lines before and after.
- Use explicit column alignments (`:---`, `:---:`, `---:`).
- Document configuration contexts, options, and defaults clearly.
- Prefer two columns; use three only for short comparable values. State shared context above the table. Put long commands in fenced blocks and explain complex settings under headings, rather than adding columns or repeating private expansion syntax.

### 5. Syntax-Highlighted Code Blocks

- Use explicit language tags: `zsh`, `bash`, `console`, `diff`.
- Present copy-pasteable snippets with accompanying expected output where helpful.

---

## Required Ecosystem Links by Archetype

Every README must provide direct markdown links to:

1. **Z-Shell Wiki:** [https://wiki.zshell.dev/](https://wiki.zshell.dev/)
2. **Issue Tracker:** `https://github.com/z-shell/<repository>/issues`
3. **Official docs for the archetype surface:** relevant sections of [https://zsh.sourceforge.io/Doc/](https://zsh.sourceforge.io/Doc/) for Zsh-facing repos, or the tool/module runtime docs when not Zsh-facing.

Additional required links for plugin-shaped repositories (plugins and annexes):

- **Zsh Plugin Standard v2:** [https://wiki.zshell.dev/community/zsh_plugin_standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
- **Zi Plugin Manager:** [https://github.com/z-shell/zi](https://github.com/z-shell/zi)

---

## Scope and Maintenance

For focused README corrections, change only the affected content. Apply the full template when creating a repository or when the requested work is a substantial README refactor.
