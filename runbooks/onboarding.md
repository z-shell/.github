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
     0008 branching model, 0009 testing/CI, 0010 security response.
3. `PATTERNS.md` and the relevant `runbooks/`.

## Step 2 — Understand the source of truth

- Active progress lives in **GitHub issues, PRs, and Linear** — not
  in local notes or agent memory.
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
  `user.signingkey`. Never add a `Co-authored-by` trailer — this is org policy.
  `z-shell/.github` enforces it in CI (`commit-lint.yml`, PRs into `main`);
  most other repositories do not have the caller wired in yet
  ([z-shell/.github#464](https://github.com/z-shell/.github/issues/464)), so
  it remains the author's responsibility there — including watching for a
  squash merge silently reintroducing the trailer even when no individual
  commit had one (`runbooks/branch-protection.md`).
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
