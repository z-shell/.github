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
4. **Technical Depth via Disclosure:** Keep advanced configuration, secondary plugin managers, and troubleshooting inside collapsible `<details>` blocks.
5. **Canon Anchoring:** Link directly to the Z-Shell Wiki and authoritative official Zsh manual sections; include plugin-standard and manager links only when the archetype uses them.

---

## Required Workflow

1. Read the repository's source, tests, workflows, local instructions, release model, and linked organization policy before drafting.
2. Place exactly one repository README at `docs/README.md` when `docs/` exists, otherwise at `.github/README.md` when `.github/` exists, and otherwise at `README.md` in the repository root. Update relative links for the chosen location, such as `../LICENSE` from `docs/` or `.github/`.
3. Classify the repository archetype and start from [`templates/readme/zsh-plugin.md`](../../../templates/readme/zsh-plugin.md) as the canonical structure:
   - **Zsh Plugins (`zsh-*`):** Follow the [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard). Document namespaced `zstyle` contexts and clean `<plugin>_plugin_unload` routines.
   - **Zi Annexes (`z-a-*`):** Keep Zi as the installation path, adapt the Lifecycle and Zi integration sections to document registered ice modifiers, annex hooks (`before_load`, `after_load`), owned state parameters, and the unload function, and keep Portable shell contract content limited to manager-independent behavior.
   - **Compiled Modules:** Adapt plugin-specific sections into module-specific build toolchain, supported Zsh/platform matrix, loader and install path, verification, and release artifact policy.
   - **Go / CLI Tools (`zsh-lint`):** Adapt plugin-specific sections into tool-specific installation, binary distribution, CLI flags, verification, and generated API reference coverage.
   - **Environment / Meta (`zd`, `wiki`):** Adapt plugin-specific sections into environment-specific targets, local preview or container workflows, verification steps, and configuration mounts.
4. Verify every feature, setting, default, alias, lifecycle claim, command, and branch statement against the current implementation.
5. For Zsh plugins and Zi annexes, lead installation guidance with Zi. Keep other manager examples concise and place them inside collapsible `<details>` disclosure blocks.
6. Keep long-form ecosystem guidance in the wiki and link to it.
7. Preserve meaningful visual identity: a clear header, a restrained maintained badge set, accessible alt text, and an optional behavior-focused screenshot or demo.
8. Do not add competitor comparisons unless comparison is the document's explicit purpose.
9. Run repository-appropriate Markdownlint, link, syntax, and behavior checks before claiming completion.

---

## Visual Design and GFM Standards

### 1. Hero Header Block
Use a centered HTML block for brand identity and status:
- Centered organization or repository logo (72x72 SVG).
- Large title and a concise tagline explaining observable value.
- Curated, uniform badge stack (flat-square style): CI workflow status, release version, license, and Zsh Plugin Standard v2 compliance.

### 2. GitHub Callout Alerts
Highlight operational details with native GFM alerts:
- `> [!TIP]` for performance optimizations (e.g. `wait lucid` turbo mode).
- `> [!NOTE]` for compatibility floors or optional dependencies.
- `> [!IMPORTANT]` for mandatory prerequisites or breaking configuration changes.
- `> [!WARNING]` for terminal constraints or known conflicts.

### 3. Collapsible Disclosures
Use `<details><summary>...</summary></details>` for:
- Secondary plugin manager recipes (Oh My Zsh, Antigen, manual sourcing).
- Advanced `zstyle` options and specialized ice modifiers.
- Migration notes from legacy or predecessor plugins.
- Troubleshooting guides and edge-case workarounds.

### 4. Tables with Proper Spacing
All tables must comply with Markdownlint MD058 and MD060:
- Surround every table with blank lines before and after.
- Use explicit column alignments (`:---`, `:---:`, `---:`).
- Document configuration contexts, options, and defaults clearly.

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
4. **Zsh Plugin Standard v2:** [https://wiki.zshell.dev/community/zsh_plugin_standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
5. **Zi Plugin Manager:** [https://github.com/z-shell/zi](https://github.com/z-shell/zi)

---

## Scope and Maintenance

For focused README corrections, change only the affected content. Apply the full template when creating a repository or when the requested work is a substantial README refactor.
