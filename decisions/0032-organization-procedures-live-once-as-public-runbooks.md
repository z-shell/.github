# 32. Organization Procedures Live Once, as Public Runbooks That Thin Skills Route To

- **Status:** ACCEPTED
- **Date:** 2026-09-26
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

[ADR-0014](0014-portable-agent-instruction-architecture.md) made this repository's `AGENTS.md` the organization baseline and required every active instruction surface to be declared in `.github/instruction-surfaces.json`. [ADR-0031](0031-per-repository-instruction-routing-delivery.md) delivers that routing into every repository and verifies vendored skill pins. Neither says where a repeatable organization procedure lives, such as triaging an issue, taking a pull request from branch to merge, or updating Project 28, nor how an agent is meant to find it.

The procedures mostly exist, as runbooks: `triage.md`, `project-tracker.md`, `release.md`, `org-review.md`, `learning-capture.md`, and thirteen more. The skills an agent discovers automatically do not reach them. Of the ten skills here, none covers triage, pull requests, the tracker, or releases, and only `code-review` and `zi-install` are vendored downstream (`knowledge/domains/agents/data/approved-skills.json`).

A review of one agent session on 2026-09-26, working through the `z-shell/zsh-lint` backlog, showed what fills that gap:

- The agent worked from its own runtime-private skills, which restated this repository's rules (the ADR-0026 fallback, branch names, the issue form, tracker fields). Those copies had drifted, and context compaction pruned them mid-session.
- Its runtime did not load the organization skills at all: project skills needed a per-worktree trust step that had not been taken.
- The outcomes that varied were the unwritten ones:
  - `Closes #470` on a pull request that met only part of the issue's acceptance criteria;
  - a merge after a post-review rebase with no new review;
  - fallback reviews carrying the ADR-0026 marker without the `code-review` checklist having run;
  - a scope question that referred to a plan the maintainer was never shown.
- The branch name `docs-488` failed the required branch-name check. The rule existed, but only in a CI workflow, which is where the agent first met it.
- Rules enforced before the pull request opened, such as the issue link and PR title, were followed.

Different runtimes and projects therefore run the same organization tasks from different private copies. That produces different outcomes and leaves nothing shared to improve when a lesson is learned.

## Decision

1. **Procedures are public and live once.** A repeatable organization procedure has one canonical text, a runbook in `runbooks/`. It is public, because maintainers, contributors, and hosted agents (Copilot) perform these tasks. A maintainer's private workspace may hold environment bindings (local paths, workspace tooling, credentials steps, generated delivery) and private policy that cannot be published, but never a second version of a public procedure.
2. **A skill is a thin router.** An organization skill contains a trigger-rich description, a short checklist, the gates that must hold, and any script that checks something mechanically. For the procedure itself it says "read `runbooks/<name>.md`" and does not restate it. This is the pattern `review-project-learning` already follows.
3. **Few skills, strong triggers.** A skill is added only for a task agents perform repeatedly, where a checklist or script adds something policy text cannot. Skills that only restate `AGENTS.md` are removed; #623 applies this to `git-commit` and `gh-cli`.
4. **Enforce what can be enforced.** A rule whose violation is detectable before merge becomes a check (CI, a validator, a workspace hook), with the runbook explaining it. Prose is for judgment.
5. **Runtime-private skills hold runtime mechanics only.** For work in z-shell repositories, a skill or memory inside one runtime's profile may describe how that runtime behaves (for example its kernel or compaction quirks), and must point to the organization skill for any organization rule. A private copy of an organization procedure is treated as drift.
6. **Delivery is verified per runtime.** Every organization skill is declared in `.github/instruction-surfaces.json`. Those meant for every repository are pinned in `knowledge/domains/agents/data/approved-skills.json` and checked by `org-routing.yml` (ADR-0031). A workspace that delivers organization skills to local runtimes verifies that each supported runtime actually discovers them, including runtimes that need an explicit trust or directory setting.

## Consequences

### Positive

- One text per procedure: a lesson learned by any agent or maintainer changes one file, and every runtime picks it up.
- Agents discover procedures through skills without loading every runbook into every session.
- Contributors and hosted agents see the same procedure the maintainer's agents follow.
- A session review can compare outcomes against a named procedure instead of against each agent's private habits.

### Costs and risks

- New runbooks and skills need writing: `pull-requests.md` does not exist, and `triage.md` needs an investigation and evidence standard.
- A thin skill costs one more file read per use; the runbook must stay readable on its own for humans.
- Runtime-private skills already in use must be cut back, and nothing stops a runtime from writing a new private copy. Periodic session reviews and the learning-capture workflow are the control.
- The skill list competes for context in runtimes that budget it (Codex gives the list at most 2% of the context window, or 8,000 characters, per [Codex's skill documentation](https://learn.chatgpt.com/docs/build-skills)), so each description must lead with its trigger words.

## Alternatives considered

1. **Keep organization management in the private meta-workspace.** Rejected: contributors and hosted agents cannot see it, and `triage.md` and `project-tracker.md` are already public, so a private version would fork them.
2. **Self-contained skills with the full procedure, and runbooks as human summaries.** Rejected: two texts per procedure drift. The session reviewed above shows the same drift between private skills and this repository's rules.
3. **Status quo, where each runtime keeps its own copies.** Rejected: it produces the varying outcomes described above and leaves nothing shared to improve.

## References

- [ADR-0014](0014-portable-agent-instruction-architecture.md), [ADR-0026](0026-review-triggers-and-fallback.md), [ADR-0031](0031-per-repository-instruction-routing-delivery.md).
- `runbooks/learning-capture.md` (destination matrix; "prefer executable prevention over prose").
- #668 (this decision's tracking issue); #623 (remove `git-commit` and `gh-cli`); #664 (maintainer-elected fallback); #642 (Copilot review availability).
- z-shell/zsh-lint #470, #486, #488, #489, #490, #491 (the session reviewed on 2026-09-26).
