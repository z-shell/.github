# Runbook — Maintainer Onboarding

How to bring a new maintainer (or a new agent operator) up to speed on the
z-shell org's conventions, permissions, and where the source of truth lives.

**Hard rule:** grant the least access that the role needs, and record who granted
it. Never share credentials or org secrets directly.

## Step 1 — Read the governing docs

Before touching anything, read, in order:

1. `AGENTS.md` (organization policy).
2. `decisions/` and `runbooks/` in this public `z-shell/.github` repository —
   the organization source for durable decisions and operational guidance.
   The accepted ADRs include:
   - 0001 meta-repo pattern, 0002 zi canonical, 0003 Conventional Commits,
     0005 workflow naming, 0006 wiki content roots, 0007 release flow,
     0009 testing/CI, 0010 security response, 0019 trunk-on-main branching.
3. `PATTERNS.md` and the relevant `runbooks/`.

## Step 2 — Understand the source of truth

- Active progress lives in **GitHub issues and pull requests**, not in local
  notes or agent memory. Project 28 is the portfolio view; Linear is a selective
  mirror, not an authority.
- This public repository's `AGENTS.md`, ADRs, and runbooks are the organization
  source for policy and operational guidance.
- Live source, repository-specific instructions, and active project state live
  in the owning repository.
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

- Clone the owning repository directly. Separate multi-repository tooling is
  optional and outside this public runbook.
- Configure commit signing: commits are signed (`gpg.format=ssh`); set a
  `user.signingkey`. A `Co-authored-by` trailer crediting a real human is
  fine — never credit a bot, AI agent, or automation as a co-author; that is
  org policy. `z-shell/.github` and `z-shell/zi` currently enforce it in CI.
  Verify every other repository's live caller and required-check configuration;
  where no verified gate exists, it remains the author's responsibility,
  including watching for a
  squash merge silently promoting a bot/agent trailer from an individual
  commit into the merge commit (`runbooks/branch-protection.md`).
- Follow Conventional Commits and the repository model in ADR-0019. Branch
  from `main` unless contributing to the named `zi` integration exception.

## Step 5 — First contribution

- Pick a `good first issue` or a triaged item.
- Branch per ADR-0019 (`feature-<id>` from `main`, or from `next` for `zi`).
- Run the class-appropriate checks locally (ADR-0009) before opening a PR.
- Leave an `Agent handoff` comment if the work will be resumed by someone else.

## See also

- `AGENTS.md`
- `decisions/`
- `runbooks/triage.md`, `runbooks/release.md`, `runbooks/adr.md`
- `runbooks/deprecation.md`
