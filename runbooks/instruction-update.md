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

## Required impact review

For every material instruction change, answer these questions in the issue or
pull-request body:

1. Is this shared policy, scoped guidance, runtime-only behavior, or enforcement?
2. Which runtimes and repository contexts must receive it?
3. Is the canonical owner still correct?
4. Does another surface now duplicate or contradict it?
5. Does either manifest need an added, changed, or removed route?
6. Can each supported runtime still receive the mandatory rule without relying on an optional hook or skill?
7. Do generated output and size limits still pass?

When the Zsh Plugin Standard or a governance reference to it changes, question
5 must also cover:

- the private control workspace's manifest routes and generated instruction
  composite; and
- the coordinated wiki change that must own the twice-yearly review automation,
  structured issue output, and deterministic page checks.

Record an explicit answer for every question. A link to this runbook without the
answers is not an impact review.

## Ordered workflow

1. Classify the rule and identify its canonical owner.
2. Enumerate every runtime and repository context that consumes it.
3. Answer all seven impact questions in the issue or pull-request body.
4. Update the canonical prose first.
5. Update the appropriate manifest entries and routes.
6. Update adapters only when runtime mechanics change; do not place policy in an
   adapter.
7. Regenerate private output when the public baseline or private overlay changes.
8. Run the public and private validators that apply to the repositories changed.
9. Perform each manual runtime discovery check or mark it unverified.
10. Review the complete diff for duplicate or contradictory ownership.
11. For Plugin Standard changes, confirm the private control-workspace route and
    coordinated wiki automation change remain aligned. Land the wiki automation
    before or with policy that depends on an active review cycle; otherwise
    record it as unresolved. Do not add a duplicate schedule here.

## Wiki (`z-shell/wiki`) checklist

- [ ] Pick the correct content root: `docs/` = Zi user docs only; `community/` = community content only; `ecosystem/` = third-party catalog. Maintainer/operational runbooks go in this repo's `runbooks/`, not the wiki. (See ADR `decisions/0006-wiki-content-root-boundaries.md`.)
- [ ] Update the wiki's local `AGENTS.md` only when wiki-specific behavior changes, and update matching `.github/instructions` for scoped behavior.
- [ ] Update `.github/instructions/docs-authoring.instructions.md` (content-root selection, frontmatter, naming).
- [ ] Update `.github/instructions/agent-docusaurus-writer.instructions.md` (root selection, invocation).
- [ ] Run `pnpm validate:frontmatter` and `pnpm build:en`.
- [ ] When the Plugin Standard changes, add or update the coordinated
      twice-yearly workflow so it opens the structured review issue and runs
      deterministic link, example, and consistency checks. Treat unlanded
      automation as a dependency, not current behavior.

## Org (`z-shell/.github`) checklist

- [ ] Decision-level change? Draft an ADR — see `runbooks/adr.md` (status starts `PROPOSED`).
- [ ] Update affected runbooks and `.github/instructions/`.
- [ ] New tooling/plugin? Update `.github/instructions/mcp-plugins.instructions.md`.
- [ ] For Plugin Standard governance, update its routed scoped guidance,
      templates, patterns, and recurring-review procedure without duplicating
      the public standard.

## Other repositories

- [ ] Update the repository's `AGENTS.md`, any required runtime adapter, and any
      scoped `.github/instructions/*.instructions.md` that describes the changed
      area.
- [ ] Prefer linking to canonical organization or wiki guidance over duplicating
      it.

## Validation commands

Run each command group only from the repository that owns it. A standalone
public repository clone does not contain the private command scripts, and the
private commands do not replace public-repository validation.

### Public-repository commands

Run from the root of a standalone `z-shell/.github` clone:

```bash
python3 scripts/validate-agent-policy.py
python3 -m unittest scripts/test_validate_agent_policy.py -v
```

### Private-meta-workspace commands

Run only from the private control-workspace root:

```bash
python3 scripts/sync-agent-instructions.py
python3 scripts/sync-agent-instructions.py --check
python3 scripts/test-agent-instructions.py
```

## Template prompt for agents

```text
I am adding <feature / content area>. Per runbooks/instruction-update.md:
- classify the rule and name its canonical owner
- enumerate every runtime and repository context that consumes it
- answer all seven impact-review questions in the issue or pull-request body
- list the canonical prose, manifest routes, adapters, generated output, validators,
  and manual runtime checks affected
Do not write code until the impact review identifies the files to change.
```
