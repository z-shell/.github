# Agent instructions — z-shell

This file is the canonical instruction set for AI coding agents working in the z-shell organization. Read it before doing non-trivial work. Repository-local guidance may narrow implementation details, but it must not silently contradict organization policy; raise any mismatch in an issue or handoff.

This file is intentionally short. It complements, not replaces:

- `.github/AGENT_MEMORY.md` for GitHub-native handoffs and shared progress
- `PATTERNS.md` for cross-repo implementation idioms
- `decisions/` for ADRs and durable architectural choices
- `runbooks/` for repeatable operational workflows

## Required instruction routing

Before non-trivial work, inspect `.github/instruction-surfaces.json`. This applies to every supported runtime. Match the current task categories and repository-relative file patterns against each manifest surface. When a surface declares both task and path dimensions, both dimensions must match before selecting it. Read every matched required surface before acting. If a runtime does not auto-load scoped guidance, open each matched required surface explicitly. Cache the result by `(repository, task class, normalized matched path set, relevant content hashes)`. Reuse it only while every key component is unchanged; otherwise reselect. When several routes select the same physical file, read it once and retain their combined provenance.

Treat byte-exact instruction content already present in the active instruction context as loaded. Manifest ownership entries and repository links do not request a second read. A byte-identical generation source already embedded in an active composite counts as loaded.

## Agent-file placement

Organization repository roots use `AGENTS.md` and permitted `.github/*` instruction surfaces. They must not contain root `CLAUDE.md` or `GEMINI.md`.

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

| Kind of information                   | Source of truth                                                              |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| Active work, blockers, next steps     | GitHub issues and pull requests                                              |
| Organization policy                   | AGENTS.md in this repository                                                 |
| Instruction routing and impact review | .github/instruction-surfaces.json and runbooks/instruction-update.md         |
| Durable architectural decisions       | `decisions/` in this repo                                                    |
| Cross-repo operational procedures     | `runbooks/` in this repo                                                     |
| Reusable implementation idioms        | `PATTERNS.md` in this repo                                                   |
| Public Zsh plugin-authoring standard  | [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard) |
| Long-form user and maintainer docs    | `wiki/` where practical                                                      |
| Local LLM memory                      | Optional cache only, never the only record                                   |

For handoffs, follow `.github/AGENT_MEMORY.md`.

## Core objective for AI assistants

When working in z-shell repositories, optimize for:

1. **Better context** — read the relevant issues, PRs, tracker items, ADRs, patterns, and repo instructions first
2. **Better reuse** — prefer existing org patterns, shared workflows, and established helper scripts over one-off inventions
3. **Better verification** — run the repo's existing checks when code changes or behavior changes
4. **Better durability** — turn non-trivial deferred work and learnings into issues, PR notes, ADRs, runbook updates, or pattern proposals

## Conventions

- **Language:** Zsh-first. Bash-only constructs are bugs in Zsh code unless the file is explicitly POSIX `sh`.
- **Zsh source:** Before reading, reviewing, diagnosing, creating, or changing Zsh source,
  classify its dialect and execution profile, identify the
  repository compatibility floor, and follow
  `.github/instructions/zsh-scripting.instructions.md`. The current released official Zsh manual
  is semantic authority. Native Zsh validity outranks
  supplemental parser, linter, or formatter limitations. Report relevant
  defects during read-only work, but that does not authorize unrelated cleanup.
- **Naming:** plugins use `zsh-<name>`, annexes use `z-a-<name>`, modules keep short descriptive names.
- **Plugin authoring:** read the canonical [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard) for plugin creation, code changes, reviews, templates, and documentation. Official Zsh documentation remains authoritative for shell semantics; manager-specific profiles are optional.
- **Canonical plugin manager:** `zi`. See `decisions/0002-zi-as-canonical-plugin-manager.md`.
- **Commits and PR titles:** Conventional Commits. See `decisions/0003-conventional-commits.md`.
- **Commit trailers:** `Co-authored-by` crediting a real human, including the PR author crediting themselves, is fine. Never credit a bot, AI agent, or automation as a co-author. `z-shell/.github` and `z-shell/zi` enforce this in CI. Other repositories remain author-enforced until their own verified caller is live; do not infer enforcement from organization policy alone.
- **Branch selection:** Follow `decisions/0019-trunk-on-main-default.md` and verify the live state of the owning repository; `zi` is the named persistent-integration exception.
- **Worktrees:** Treat `git worktree list --porcelain` as the authoritative inventory. Use the owning repository's declared helper and stable worktree root; do not create worktrees in `/tmp` or another ad hoc location. Do not use a linked superproject checkout for work that needs initialized submodules. Follow `runbooks/worktrees.md`.
- **Documentation placement:** keep long-form docs in the wiki when practical; keep repo-local docs focused on policy, workflow, and source-adjacent guidance.
- **Workflow files:** follow the org workflow conventions and keep permissions explicit, actions pinned, and concurrency defined.
- **Dependency updates:** Renovate owns routine version updates; GitHub Dependabot owns vulnerability alerts and security updates. See `runbooks/dependency-management.md`.

## Before editing

1. Read this file, then any repo-local `AGENTS.md` or `.github/copilot-instructions.md`.
2. Search the owning repository for open issues and pull requests related to the task.
3. Check linked tracker items and previous handoff comments.
4. Read the relevant ADRs, patterns, and runbooks.
5. For cross-repo questions, search the organization before assuming the local repo is unique.
6. If no issue exists for non-trivial planned work, propose one. Create it only
   when explicit external-write authority is present.
7. For substantive work, verify that the owning issue is in Z-shell Delivery
   (Project 28), with its triage state visible before implementation starts.

Creating or updating issues, comments, pull requests, or tracker records requires explicit external-write authority. Without that authority, report the proposed external write instead.

## While editing

- Match the nearest established pattern instead of introducing a new local style.
- Keep changes reviewable and scoped; separate mechanical cleanup from behavioral change.
- Update nearby docs, templates, or runbooks when your change makes them inaccurate.
- Avoid creating a second conflicting source of truth. Extend the canonical file instead.
- Record material progress, blockers, review readiness, and handoff on the
  owning issue or pull request. Assignment alone is not evidence of active
  management.

## Before claiming done

- Run the repo's existing checks when the change affects behavior, CI, workflows, or generated outputs.
- For documentation-only edits, at minimum make sure links, paths, and examples are internally consistent.
- If work is unfinished, blocked, or likely to be resumed later, leave an `Agent handoff` comment using `.github/AGENT_MEMORY.md`.
- Convert deferred follow-up work into issues instead of leaving it only in local notes.

## Triage and recurring operations

Use `runbooks/triage.md` for issue and pull-request triage and
`runbooks/recurring-operations.md` for recurring organization workflows. Keep
the first pass non-destructive and, unless a maintainer asks otherwise, produce
drafts only.

For coordinated outcomes, parent issues, sub-issues, and issue dependencies,
follow `runbooks/sub-issues.md`.

## Security

- Never print, commit, or hand off secrets, tokens, or personal data.
- Never commit `.env*` files other than placeholders such as `.env.example`.
- Do not add network activity to plugin load paths unless it is an explicit user action.
- Treat all user-supplied shell input as untrusted.

## PR conventions

- Prefer squash merges unless a branch genuinely needs separate commits
  preserved. `zi` promotion from persistent `next` to stable `main` is the
  ancestry-preserving merge-commit exception defined by ADR-0019.
- Link the related issue, PR, tracker item, or ADR.
- When a PR makes or codifies a non-obvious decision, draft or update an ADR.
- For unfinished work, include an `Agent handoff` section in the PR body or issue thread.

## Learning capture

Before claiming non-trivial work complete, perform a learning and reuse review
using `runbooks/learning-capture.md`.

`No durable learning` is a valid silent result. Promote a finding only when it
is evidence-backed, likely to recur, and routed to the smallest existing
canonical owner. Prefer executable checks over prose. Do not create memory,
instructions, skills, issues, ADRs, runbooks, or documentation merely to show
that the review happened.

Hooks and skills may remind or guide the review, but they are optional and
cannot own this mandatory rule.

## When this file is wrong

Do not silently work around drift. Propose an issue in `z-shell/.github` that
explains what is wrong and links the contradicting repository state. Open or
update it only when explicit external-write authority is present.

## See also

- `.github/AGENT_MEMORY.md`
- `.github/instruction-surfaces.json`
- `PATTERNS.md`
- [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
- `decisions/`
- `runbooks/org-review.md`
- `runbooks/adr.md`
- `runbooks/dependency-management.md`
- `runbooks/labels.md`
- `runbooks/instruction-update.md`
- `runbooks/new-repository.md`
- `runbooks/project-tracker.md`
- `runbooks/release.md`
- `runbooks/sub-issues.md`
- `runbooks/triage.md`
