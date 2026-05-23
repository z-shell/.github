# 5. No Emojis in Workflow and Job Name Fields

- **Status:** ACCEPTED
- **Date:** 2026-05-21
- **Deciders:** ss-o, Claude Code
- **Supersedes:** None
- **Superseded by:** None

## Context

GitHub Actions workflow `name:` and job `name:` fields appear in the GitHub Actions tab and in CI status surfaces such as branch protection checks and PR status badges. Across the z-shell organization, these fields had been inconsistently styled:

- ~26 workflow files used emoji prefixes (e.g., `🐧 Check (Linux)`, `"🛳  Deploy Wiki"`, `"📦 Dependency Review"`)
- ~9 workflow files used plain text (e.g., `CodeQL`, `Trunk Code Quality`, `ZUnit (native)`)

The canonical CLAUDE.md example table already showed plain-text names, and the instruction file for workflow conventions made no explicit statement either way, allowing drift to accumulate.

Emoji in step `name:` fields is a different concern: step names appear inside job logs where visual landmarks genuinely aid scanning. That context is preserved.

## Decision

1. **Workflow `name:` fields** — plain text only, no emoji prefix or suffix.
2. **Job `name:` fields** — plain text only, no emoji prefix or suffix.
3. **Step `name:` fields** — emoji allowed; useful for scanning long job logs.
4. Use title case or sentence case for workflow and job names, consistent within each repo.
5. Keep names short (≤ 50 chars for workflow names — shown in the Actions tab).

Apply this rule to all existing workflow files and all new workflows going forward.

## Consequences

### Positive

- Consistent, professional appearance in the Actions tab and CI status surfaces.
- Easier to grep, script, and reference names without Unicode handling.
- New contributors and agents have a single clear rule instead of inherited ambiguity.

### Negative / costs

- One-time mechanical change across ~26 existing workflow files.
- The `workflow-templates/` in this repo must also be updated so new repos start clean.

### Neutral

- Step names are unaffected; long-log readability is preserved.

## Alternatives considered

1. **Emojis everywhere** — standardize on a canonical emoji per workflow category. Rejected: requires ongoing governance of emoji assignments and makes names harder to script against.
2. **Per-repo choice** — each repo decides. Rejected: this is exactly what produced the current drift; the organization benefits from one standard.
3. **Trunk custom lint check** — add a grep-based custom linter to `trunk.yaml`. Rejected for now: the org has no precedent for custom Trunk lint definitions, and the documentation layers (this ADR, `github-actions-ci-cd-best-practices.instructions.md`, workspace CLAUDE.md) are the established enforcement mechanism for style rules.

## References

- `AGENTS.md`
- `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
- `PATTERNS.md`
- Workspace `CLAUDE.md` (workflow naming conventions section)
