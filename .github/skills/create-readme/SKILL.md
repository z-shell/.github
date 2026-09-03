---
name: create-readme
description: "Create or refactor a repository README with polished GFM styling, valuable links, and high-clarity structure"
---

# Create README

Create an accurate, visually polished, and technically rigorous repository landing page using GitHub Flavored Markdown (GFM).

## Core Objectives

1. **Immediate Clarity:** Communicate the project's purpose and observable value within the first viewport.
2. **Visual Polish without Bloat:** Use clean typography, centered hero headers, uniform badge rows, and native GFM callouts.
3. **Frictionless Onboarding:** Lead with a 5-second Zi quick-start snippet, followed by concise usage examples.
4. **Technical Depth via Disclosure:** Keep advanced configuration, secondary plugin managers, and troubleshooting inside collapsible `<details>` blocks.
5. **Canon Anchoring:** Link directly to the Z-Shell Wiki, Zsh Plugin Standard v2, and authoritative official Zsh manual sections.

---

## Required Workflow

1. Read the repository's source, tests, workflows, local instructions, release model, and linked organization policy before drafting.
2. Classify the repository archetype:
   - **Zsh Plugins (`zsh-*`):** Use [`templates/readme/zsh-plugin.md`](../../../templates/readme/zsh-plugin.md) as the canonical structure and follow the [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard). Document namespaced `zstyle` contexts and clean `<plugin>_plugin_unload` routines.
   - **Zi Annexes (`z-a-*`):** Document registered ice modifiers, annex hooks (`before_load`, `after_load`), and integration with `zi`.
   - **Compiled / Go Tools (`zsh-lint`):** Document binary installation, Go module paths, CLI flags, and generated API references.
   - **Environment / Meta (`zd`, `wiki`):** Document container targets, local preview servers, and configuration mounts.
3. Verify every feature, setting, default, alias, lifecycle claim, command, and branch statement against the current implementation.
4. Lead Zsh-plugin installation guidance with Zi. Keep other manager examples concise and place them inside collapsible `<details>` disclosure blocks.
5. Keep long-form ecosystem guidance in the wiki and link to it.
6. Preserve meaningful visual identity: a clear header, a restrained maintained badge set, accessible alt text, and an optional behavior-focused screenshot or demo.
7. Do not add competitor comparisons unless comparison is the document's explicit purpose.
8. Run repository-appropriate Markdownlint, link, syntax, and behavior checks before claiming completion.

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

## Mandatory Ecosystem Links

Every README must provide direct markdown links to:
1. **Z-Shell Wiki:** [https://wiki.zshell.dev/](https://wiki.zshell.dev/)
2. **Zsh Plugin Standard v2:** [https://wiki.zshell.dev/community/zsh_plugin_standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
3. **Official Zsh Manual:** Specific relevant sections of [https://zsh.sourceforge.io/Doc/](https://zsh.sourceforge.io/Doc/) (e.g. Zstyle, ZLE, Shell Builtins).
4. **Zi Plugin Manager:** [https://github.com/z-shell/zi](https://github.com/z-shell/zi)
5. **Issue Tracker:** `https://github.com/z-shell/<repository>/issues`

---

## Scope and Maintenance

For focused README corrections, change only the affected content. Apply the full template when creating a repository or when the requested work is a substantial README refactor.
