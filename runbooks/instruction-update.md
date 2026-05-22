# Runbook — Instruction Update

Use this workflow to keep agent and contributor instructions current when the
codebase gains a feature, infrastructure component, or new content area. It is
the living checklist that answers "which instruction files need updating when I
change something?"

## When to use this

Run this before opening a PR that:

- adds a new content area, page section, or directory to a repository
- introduces a new feature, service, or infrastructure component
- changes a convention, boundary, or workflow that an instruction file describes

Skip it for pure bug fixes or content edits that do not change any documented
convention.

## Wiki (`z-shell/wiki`) checklist

- [ ] Pick the correct content root: `docs/` = Zi user docs only; `community/` = community content only; `ecosystem/` = third-party catalog. Maintainer/operational runbooks go in this repo's `runbooks/`, not the wiki. (See ADR `decisions/0006-wiki-content-root-boundaries.md`.)
- [ ] Update `AGENTS.md` if scope or conventions changed. `CLAUDE.md` is a symlink to `AGENTS.md`, so it updates automatically.
- [ ] Update `.github/instructions/docs-authoring.instructions.md` (Content Root Selection, frontmatter, naming).
- [ ] Update `.github/instructions/agent-docusaurus-writer.instructions.md` (root selection, invocation).
- [ ] Run `pnpm validate:frontmatter` and `pnpm build:en`.

## Org (`z-shell/.github`) checklist

- [ ] Decision-level change? Draft an ADR — see `runbooks/adr.md` (status starts `PROPOSED`).
- [ ] Update affected runbooks and `.github/instructions/`.
- [ ] New tooling/plugin? Update `.github/instructions/mcp-plugins.instructions.md`.

## Other repos

- [ ] Update the repo's `AGENTS.md` / `.github/copilot-instructions.md` and any scoped `.github/instructions/*.instructions.md` that describe the changed area.
- [ ] Prefer linking to canonical org/wiki guidance over duplicating it.

## Template prompt for agents

```text
I am adding <feature / content area>. Per runbooks/instruction-update.md:
- which content root applies (wiki)?
- which instruction files and ADRs need updating?
- does this decision warrant a new ADR?
List the files to touch before writing code.
```
