---
description: "Where documentation lives across z-shell repos and the wiki content-root boundaries"
applyTo: "**"
---

# Documentation Instructions

Where a piece of documentation belongs, and the wiki's content-root rules. This
operationalizes `decisions/0006-wiki-content-root-boundaries.md` and the
org-wide documentation policy.

## Default home: the wiki

Durable, long-form documentation belongs in `z-shell/wiki` whenever practical.
Keep individual repos lean by linking to wiki pages instead of duplicating
guidance. Repo-local docs are justified only when tightly coupled to that repo's
source, release process, or contributor workflow.

When a repo-local copy is unavoidable, prefer a generated or synchronized file
sourced from the wiki so maintenance stays centralized and drift is minimized.

## Wiki content-root boundaries (ADR-0006)

The wiki has three independent content roots. Place content by audience and
purpose, not by topic:

- **`docs/`** — Zi **end-user** documentation: getting started, usage, guides for
  people _using_ the tools.
- **`community/`** — community-facing material: standards, contribution norms,
  ecosystem-wide conventions.
- **`ecosystem/`** — ecosystem catalog: plugins, annexes, and related projects.

Maintainer/operational guides are **not** end-user docs — do not place them under
`docs/` just because they concern the tools.

### Hard rules

- Do not create a duplicate of the same page across two content roots. A page has
  one canonical home; link to it from elsewhere.
- When "moving" a page between roots, reconcile content rather than copying
  verbatim — the ADR-0006 failure was a literal move that would have shipped
  stale secret-key naming. Verify the moved copy matches current code/config.
- Never commit secret values or stale secret-key names in docs; reference the
  current canonical names only.

## Repository READMEs

Every maintained repository has exactly one repository landing README. Place it at `docs/README.md` when `docs/` exists, otherwise at `.github/README.md` when `.github/` exists, and otherwise at `README.md` in the repository root. Do not create `docs/` solely to hold the README. Update relative links for the selected location, such as `../LICENSE` from `docs/` or `.github/`.

When creating a repository README or substantially restructuring one, start from [`templates/readme/zsh-plugin.md`](../../templates/readme/zsh-plugin.md). A focused correction does not require an unrelated full rewrite. The template standardizes the common information order and accessible visual hierarchy; adapt plugin-specific headings, examples, links, and checklist items to the repository archetype:

- **Zsh plugins:** lead installation with Zi, follow the [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard), and document namespaced configuration plus exact load and unload behavior.
- **Zi annexes:** use the Zi installation path and document registered ice modifiers, annex hooks, owned state, unload behavior, and only manager-independent portable behavior.
- **Compiled modules:** document the build toolchain, supported Zsh and platform matrix, loader and installation paths, verification, and release artifacts.
- **Tools and environment/meta repositories:** document the applicable runtime, installation or deployment path, public interface, verification, and release or deployment model without adding plugin-only claims.

Link to authoritative documentation for the archetype. Use the official Zsh manual for Zsh-facing repositories; use the applicable runtime or tool documentation when the repository is not Zsh-facing. Plugin Standard and plugin-manager requirements apply only to plugin-shaped repositories.

## Line wrapping

Write prose one paragraph per line, and one list item per line. Do not hard-wrap at a column width.

GitHub renders repository `.md` files with soft breaks, so wrapping changes nothing on the page there; it only makes a one-word edit reflow every following line of the paragraph, and reviews and blame then show whole-paragraph churn. Issue bodies, pull-request bodies, comments, release notes, discussions, and the `markdown` blocks inside issue forms render every newline as a line break, so wrapped text there is a visible defect. One rule for both targets is simpler than remembering which renderer applies.

Do not reflow a pre-existing wrapped paragraph unless you are already editing it. Reflowing a whole repository is mechanical cleanup and lands as its own pull request. When a repository uses Prettier for Markdown, leave wrapping at the default `preserve` behavior unless a separately documented need requires otherwise; that keeps one-paragraph-per-line prose as written and does not collapse multi-line GitHub alert blocks in README templates.

## LLM/agent files

Keep shared organization guidance in z-shell/.github. Keep child-repository AGENTS.md or .github/instructions files only for concise repository-specific behavior, and link to public canonical guidance rather than duplicating it.

## See also

- `decisions/0006-wiki-content-root-boundaries.md`
- [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
- `z-shell/wiki:.github/copilot-instructions.md` (wiki-local authoring rules)
- `z-shell/wiki:.github/instructions/docs-authoring.instructions.md`
