# Agent instructions — z-shell

This file is the canonical instruction set for AI coding agents working in the z-shell organization. Read it before doing non-trivial work. If repository-local instructions conflict with this file, follow the repo-local file for repo-specific detail and raise the mismatch in an issue or handoff.

This file is intentionally short. It complements, not replaces:

- `.github/AGENT_MEMORY.md` for GitHub-native handoffs and shared progress
- `PATTERNS.md` for cross-repo implementation idioms
- `decisions/` for ADRs and durable architectural choices
- `runbooks/` for repeatable operational workflows

## What z-shell is

z-shell is an ecosystem of tools, plugins, annexes, modules, and documentation centered on Zsh and the `zi` plugin manager.

The broad shapes are:

1. **`zi`** — the canonical plugin manager for the ecosystem
2. **Annexes** (`z-a-*`) — extensions that target `zi`
3. **Plugins** (`zsh-*`) — end-user features, preferably plugin-manager-agnostic where practical
4. **Modules and libraries** — lower-level building blocks such as `zredis`
5. **Documentation and org infrastructure** — `wiki`, `.github`, CI, templates, and shared policy

## Sources of truth

Use the right home for each kind of knowledge:

| Kind of information                | Source of truth                                       |
| ---------------------------------- | ----------------------------------------------------- |
| Active work, blockers, next steps  | GitHub issues, pull requests, and Linear |
| Private organizational heuristics  | `memory/` folder in the root meta-workspace           |
| Durable architectural decisions    | `decisions/` in this repo                             |
| Cross-repo operational procedures  | `runbooks/` in this repo                              |
| Reusable implementation idioms     | `PATTERNS.md` in this repo                            |
| Long-form user and maintainer docs | `wiki/` where practical                               |
| Local LLM memory                   | Optional cache only, never the only record            |

For handoffs, follow `.github/AGENT_MEMORY.md`.

## Core objective for AI assistants

When working in z-shell repositories, optimize for:

1. **Better context** — read the relevant issues, PRs, tracker items, ADRs, patterns, and repo instructions first
2. **Better reuse** — prefer existing org patterns, shared workflows, and established helper scripts over one-off inventions
3. **Better verification** — run the repo's existing checks when code changes or behavior changes
4. **Better durability** — turn non-trivial deferred work and learnings into issues, PR notes, ADRs, runbook updates, or pattern proposals

## Conventions

- **Language:** Zsh-first. Bash-only constructs are bugs in Zsh code unless the file is explicitly POSIX `sh`.
- **Naming:** plugins use `zsh-<name>`, annexes use `z-a-<name>`, modules keep short descriptive names.
- **Canonical plugin manager:** `zi`. See `decisions/0002-zi-as-canonical-plugin-manager.md`.
- **Commits and PR titles:** Conventional Commits. See `decisions/0003-conventional-commits.md`.
- **Documentation placement:** keep long-form docs in the wiki when practical; keep repo-local docs focused on policy, workflow, and source-adjacent guidance.
- **Workflow files:** follow the org workflow conventions and keep permissions explicit, actions pinned, and concurrency defined.

## Before editing

1. Read this file, then any repo-local `AGENTS.md` or `.github/copilot-instructions.md`.
2. Search the owning repository for open issues and pull requests related to the task.
3. Check linked tracker items and previous handoff comments.
4. Read the relevant ADRs, patterns, and runbooks.
5. For cross-repo questions, search the organization before assuming the local repo is unique.
6. If no issue exists for non-trivial planned work, create one in the owning repository.

## While editing

- Match the nearest established pattern instead of introducing a new local style.
- Keep changes reviewable and scoped; separate mechanical cleanup from behavioral change.
- Update nearby docs, templates, or runbooks when your change makes them inaccurate.
- Avoid creating a second conflicting source of truth. Extend the canonical file instead.

## Before claiming done

- Run the repo's existing checks when the change affects behavior, CI, workflows, or generated outputs.
- For documentation-only edits, at minimum make sure links, paths, and examples are internally consistent.
- If work is unfinished, blocked, or likely to be resumed later, leave an `Agent handoff` comment using `.github/AGENT_MEMORY.md`.
- Convert deferred follow-up work into issues instead of leaving it only in local notes.

## Triage and prioritization

Use `runbooks/triage.md` for the full process.

Short version:

- Classify issues by work type, area, and severity.
- Use the canonical labels from `.github/lib/labels.yml`.
- Search for prior art across the org before responding.
- Put cross-repo, release-blocking, security, or strategic work on Linear.

## Draft-only workflows

For recurring organization workflows, prefer the runbooks and keep the first pass non-destructive:

- weekly org review: `runbooks/org-review.md`
- issue and PR triage: `runbooks/triage.md`
- label maintenance: `runbooks/labels.md`
- project tracker automation: `runbooks/project-tracker.md`
- new-repository bootstrap: `runbooks/new-repository.md`
- ADR drafting: `runbooks/adr.md`
- release coordination and release-model classification: `runbooks/release.md`

Unless a maintainer asks otherwise, these workflows produce drafts only.

## Security

- Never print, commit, or hand off secrets, tokens, or personal data.
- Never commit `.env*` files other than placeholders such as `.env.example`.
- Do not add network activity to plugin load paths unless it is an explicit user action.
- Treat all user-supplied shell input as untrusted.

## PR conventions

- Prefer squash merges unless a branch genuinely needs separate commits preserved.
- Link the related issue, PR, tracker item, or ADR.
- When a PR makes or codifies a non-obvious decision, draft or update an ADR.
- For unfinished work, include an `Agent handoff` section in the PR body or issue thread.

## Learning capture

Non-trivial sessions should end with durable follow-up, not silent local memory. If you discover:

- a pattern used in at least two repositories
- a decision that should be recorded
- a runbook gap
- a tooling gap

capture it in the relevant issue, PR, or draft change to `PATTERNS.md`, `decisions/`, or `runbooks/` for human review.

## When this file is wrong

Do not silently work around drift. Open or update an issue in `z-shell/.github`, explain what is wrong, and link the contradicting repository state.

## See also

- `.github/AGENT_MEMORY.md`
- `PATTERNS.md`
- `decisions/`
- `runbooks/org-review.md`
- `runbooks/adr.md`
- `runbooks/labels.md`
- `runbooks/new-repository.md`
- `runbooks/project-tracker.md`
- `runbooks/release.md`
- `runbooks/triage.md`
