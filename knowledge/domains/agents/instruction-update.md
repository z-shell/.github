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

## Consumer audiences

Keep `consumers` required. Use `agent` for portable guidance intended for any coding agent, `human` for people, and `ci` for automated checks. Shared policy, runbooks and portable skills normally use `["agent", "human"]`; include `ci` only when applicable. This avoids enumerating every current or future runtime on shared surfaces.

Keep concrete runtime consumers on adapters and guidance whose mechanics are runtime-specific. Existing runtime identifiers remain valid for compatibility; do not rename a Gemini adapter to Antigravity without verifying its actual file and loading contract. Audience declarations describe intended applicability, not successful discovery, installation or invocation. Verify delivery separately for each runtime under ADR-0014 and ADR-0032.

`consumers` does not replace task and path selectors or authorize actions. The downstream routing generator continues to select declared surfaces by tasks, file patterns and approved vendored skills. Do not broaden a targeted surface to `agent` solely to make an inventory look complete.

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
- [ ] New tooling/plugin? Update `.github/instructions/agents/tool-integration.instructions.md`.
- [ ] For Plugin Standard governance, update its routed scoped guidance,
      templates, patterns, and recurring-review procedure without duplicating
      the public standard.

## Other repositories

- [ ] Update the repository's `AGENTS.md`, any required runtime adapter, and any
      scoped `.github/instructions/*.instructions.md` that describes the changed
      area. Edit only outside the `org-routing` markers; the block between them
      is generated (decisions/0031).
- [ ] Adding, removing, or renaming a routable surface (scoped
      instructions, agent, prompt, or local skill) or vendoring an
      organization skill is a `downstream` change in this repository's
      `.github/instruction-surfaces.json`. Land it here first, then regenerate
      the repository's block with
      `python3 automation/agents/org-routing.py apply --repository z-shell/<name> --root <checkout>`
      and verify with `check`.
- [ ] Prefer linking to canonical organization or wiki guidance over duplicating
      it.

## Validation commands

Run each command group only from the repository that owns it. A standalone
public repository clone does not contain the private command scripts, and the
private commands do not replace public-repository validation.

### Public-repository commands

Run from the root of a standalone `z-shell/.github` clone:

```bash
python3 automation/agents/validate-agent-policy.py
python3 -m unittest automation/agents/test_validate_agent_policy.py -v
python3 automation/agents/org-routing.py validate
python3 automation/agents/org-routing.py verify-approved
python3 -m unittest automation/agents/test_org_routing.py -v
```

An approved skill comes from `z-shell/.github` unless its record names another approved `source` (decisions/0037); such a record also declares the `tasks` that select its vendored copy, since no organization surface describes it. `verify-approved` reads each skill from a full-history checkout of its own source and fails when none is given: pass one `--source-root OWNER/REPO=PATH` per other source, for example `--source-root z-shell/agent-skills=../agent-skills`. Its vendored copy still lives at `.github/skills/<name>`, and `check` requires its installer metadata to name that source.

### Private-meta-workspace commands

Run only from the private control-workspace root:

```bash
python3 scripts/sync-agent-instructions.py
python3 scripts/sync-agent-instructions.py --check
python3 scripts/test-agent-instructions.py
```

## Read-only change-impact report

Before editing consumers, run `python3 automation/agents/org_policy_report.py impact --changed runbooks/triage.md` from the organization checkout. Repeat `--changed` for every added, modified, renamed or removed path, including both names of a rename. The JSON report uses the existing manifest and approved-skill inventory: shared policy selects all declared consumers for review, while approved skill changes select their declared vendors. Editable sources in knowledge/delivery.json receive their generated consumer's relationship and review candidates; the report records the delivery map's content hash. Workflow, action and template changes explicitly require a caller inventory. Unmapped paths remain visible for manual review. This is a conservative review list, not a complete prose-reference graph or permission to edit consumers.

The report does not advance approved revisions. Merge an approved-source change before downstream re-pinning; verify each caller against both its pinned tooling and the intended current baseline. A passing check at an older pin establishes compatibility with that pin, not currency with newer policy.

Complete project instructions use knowledge/project-delivery.json in the same routing pipeline. Follow [central knowledge maintenance](knowledge-maintenance.md) for the record schema, approved-source rendering and project compatibility boundary. apply writes only the selected complete consumers and generated routing block after preflight; check rejects content, provenance and selector drift. verify-approved validates organization source commits and blobs with full history. The change-impact report selects declared project consumers for their source changes and binds its observations to the project delivery manifest hash.

`org-routing.py check` discovers tracked and non-ignored files when its target is a Git checkout. Tracked files remain checked even if an ignore rule matches them; required declared files and vendored resources are always checked. Ignored dependency files are outside this repository-content check. Exported trees without their own Git metadata retain filesystem discovery. This boundary does not establish that a runtime ignores ambient local guidance; runtime discovery remains a separate observation.

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
