# 6. Wiki Content-Root Boundaries

- **Status:** PROPOSED
- **Date:** 2026-05-22
- **Deciders:** ss-o, Claude Code
- **Supersedes:** None
- **Superseded by:** None

## Context

The Docusaurus wiki (`z-shell/wiki`) has three independent content roots — `docs/`, `community/`, and `ecosystem/`. The wiki `AGENTS.md` described `docs/` only as "core documentation, getting started, guides", which is ambiguous: it does not distinguish Zi end-user documentation from maintainer or operational content.

That ambiguity caused a concrete failure. A maintainer guide (Supabase Knowledge Search) was placed under `docs/maintainers/`, then half-moved to `community/`, leaving a divergent duplicate. The `community/` copy was untracked and carried stale secret-key naming (`SUPABASE_SERVICE_ROLE_KEY`), while the canonical `docs/` copy matched the code (`SB_SECRET_KEY` / `SUPABASE_SECRET_KEY`). A literal "move" would have shipped the stale naming.

## Decision

The three content roots have fixed, non-overlapping scopes:

1. `docs/` is **Zi plugin-manager user documentation only** — installation, commands, usage guides.
2. `community/` holds **Z-Shell ecosystem community content only** — contributing, the Zsh handbook/plugin standard, ZUnit.
3. `ecosystem/` holds the third-party catalog: annexes, packages, plugins.

Maintainer, operational, and infrastructure runbooks do not belong on the public wiki at all. They live in `z-shell/.github/runbooks/` (e.g. `runbooks/supabase-knowledge-search.md`), which is the established home for operational documentation. Feature *implementation* (Edge Functions, migrations, scripts) still lives in the owning repository.

These boundaries are recorded in the wiki `AGENTS.md` (with `CLAUDE.md` as a symlink to it) and the wiki authoring instructions (`docs-authoring.instructions.md`, `agent-docusaurus-writer.instructions.md`).

## Consequences

- Maintainer/operational runbooks live in `z-shell/.github/runbooks/`, not anywhere in the public wiki. The Supabase Knowledge Search guide was relocated from `wiki/community/10_maintainers/` to `runbooks/supabase-knowledge-search.md`.
- Authoring instructions gain a Content Root Selection table; `docs/` and `community/` both exclude maintainer/operational content.
- The `runbooks/instruction-update.md` runbook keeps instructions in sync when new features or content areas are added.

> **Revision (2026-05-22):** An earlier draft placed maintainer/operational tooling under `community/`. Review concluded such content (secret names, infrastructure topology, ops CLIs) should not be published on the public wiki at all, so it now routes to `z-shell/.github/runbooks/`.

## Alternatives considered

- **Add a fourth `maintainers/` content root.** Rejected: more navbar/config surface for a small amount of content, and it would still publish maintainer/operational surface on the public wiki.
- **Leave the guide in `docs/` and document an exception.** Rejected: keeps the ambiguity that caused the incident and invites future drift.
- **CI placement guard only (no instruction change).** Deferred: automation without a documented rule is brittle; document first, automate later if manual enforcement proves insufficient.

## References

- `z-shell/wiki` PR #736 — move maintainer tooling to `community/` and define content-root boundaries.
- `runbooks/instruction-update.md` — the maintenance routine this ADR establishes.
