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
  people *using* the tools.
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

## Zsh plugin READMEs

Use [`templates/readme/zsh-plugin.md`](../../templates/readme/zsh-plugin.md)
when creating a Zsh plugin repository or substantially restructuring its
README. Focused corrections do not require an unrelated full rewrite.

The template standardizes required information and visual hierarchy, not
identical prose or artwork. Zi remains the first installation path. Include a
screenshot or short demo only when it materially explains behavior, and keep
long-form ecosystem guidance in the wiki.

## LLM/agent files

Per the workspace LLM file-placement policy, keep generic agent instructions
centralized in the meta-workspace root or `z-shell/.github`. Child repos keep
`AGENTS.md` / `.github/instructions/` only for repo-specific workflows that
cannot be expressed centrally, and those should link back rather than repeat
shared policy.

## See also

- `decisions/0006-wiki-content-root-boundaries.md`
- `repos/docs/wiki/.github/copilot-instructions.md` (wiki-local authoring rules)
- `repos/docs/wiki/.github/instructions/docs-authoring.instructions.md`
