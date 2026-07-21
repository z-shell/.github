# Runbook — Maintainer Onboarding

How to bring a new maintainer (or a new agent operator) up to speed on the
z-shell org's conventions, permissions, and where the source of truth lives.

**Hard rule:** grant the least access that the role needs, and record who granted
it. Never share credentials or org secrets directly.

## Step 1 — Read the governing docs

Before touching anything, read, in order:

1. `AGENTS.md` (org-level instructions) and the workspace `CLAUDE.md`.
2. `decisions/` — the accepted ADRs. These are the durable rules:
   - 0001 meta-repo pattern, 0002 zi canonical, 0003 Conventional Commits,
     0005 workflow naming, 0006 wiki content roots, 0007 release flow,
     0008 branching model, 0009 testing/CI, 0010 security response.
3. `PATTERNS.md` and the relevant `runbooks/`.

## Step 2 — Understand the source of truth

- Active progress lives in **GitHub issues, PRs, and Linear** — not
  in local notes or agent memory.
- `.gitmodules` is the Git-native source of truth for child-repo paths/remotes;
  the meta-workspace `workspace/repos.yml` is the human/LLM-readable catalog.
- Durable decisions go in `decisions/`; long-form docs go in the wiki.

## Step 3 — Permissions (least privilege)

Grant only what the role requires; record the grant:

- **Triage:** issue/PR triage and labels (per `runbooks/triage.md`).
- **Write:** branch + PR on assigned repos. Direct pushes to publication branches
  are avoided; use PRs.
- **Maintain/Admin:** reserved for accepting ADRs (see `runbooks/adr.md` decision
  authority), managing required checks, and org settings.
- Org secrets (e.g. `DISALLOWED_TRAILER_PATTERN`, project tokens) are never shared
  in plaintext or inlined in workflow YAML.

## Step 4 — Local environment

- Clone via the meta-workspace; child repos are submodules. Note that **git
  worktrees do not check out submodules** — child-repo work happens in the main
  clone.
- Configure commit signing: commits are signed (`gpg.format=ssh`); set a
  `user.signingkey`. Never add a `Co-authored-by` trailer — this is org policy,
  and note that no default-branch CI currently enforces it, so it is author's
  responsibility, not a gate that will catch a mistake.
- Follow Conventional Commits and the branch model for the repo's class
  (ADR-0008).

## Step 5 — First contribution

- Pick a `good first issue` or a triaged item.
- Branch per ADR-0008 (`feature-<id>` from `next` or `main` by class).
- Run the class-appropriate checks locally (ADR-0009) before opening a PR.
- Leave an `Agent handoff` comment if the work will be resumed by someone else.

## See also

- `AGENTS.md`
- `decisions/`
- `runbooks/triage.md`, `runbooks/release.md`, `runbooks/adr.md`
- `runbooks/deprecation.md`
