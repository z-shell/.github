# Runbook — Weekly org review

Use this workflow to turn organization-wide GitHub activity into a short prioritized draft for maintainers.

**Hard rule:** this workflow produces a draft only. Do not edit repositories,
install or update skills, trigger hosted reviews, label, comment, close, merge,
or file follow-up issues unless a maintainer explicitly authorizes that action.

## Goal

Create a one-pass weekly review that answers:

- what changed across the organization in the last 7 days
- what needs attention now
- which issues or PRs appear to be part of the same cross-repo pattern
- which follow-up items should be proposed to maintainers

## Inputs

- GitHub issues and pull requests across the z-shell organization
- relevant tracker items
- recent workflow failures where they materially affect maintainer priority

## Output shape

Return a draft with these sections:

1. **Urgent**
2. **Needs review**
3. **Cross-repo patterns**
4. **Suggested follow-ups**

Each item should link the source issue, PR, or workflow and explain why it matters in one sentence.

## Review steps

1. Summarize new issues opened in the last 7 days by repository.
2. List PRs waiting for review longer than 3 days.
3. Flag regressions, security issues, or release blockers.
4. Look for repeated symptoms or the same maintenance task across multiple repositories.
5. Suggest the smallest useful follow-up action for each important item.
6. Whenever evaluating repository health, complete the review-readiness checks
   below, including in quick evaluations.

## Repository-health review readiness

Include every repository in the requested scope. For an organization-wide
review, discover the live repository inventory with complete pagination;
local clone catalogs alone are not organization-wide coverage. List archived
repositories as excluded unless explicitly in scope. Assess maintained forks
individually against their upstream constraints. Report inaccessible and
unassessed repositories, never omit them from coverage counts.

Record the repository, assessed revision or local working-tree state, component
classes, and these results for each repository:

- **Presence and validity:** `.github/skills/code-review/SKILL.md` is a regular
  file in a standalone checkout, with valid YAML frontmatter naming
  `code-review`, a non-empty review-focused description, and actionable body.
  Any bundled references must resolve within the skill; repository guidance
  must be discovered conditionally or linked to an accessible canonical source.
  Reject broken links, missing required resources, and host-specific paths.
- **Provenance and currency:** identify the approved canonical source revision in `z-shell/.github`, the installed revision, and any difference from the approved source. Compare the actual skill content and resource inventory, accounting only for installer-added source metadata; `org-routing.py check` compares `SKILL.md` by its approved digest and every other skill file by its approved Git blob id. Metadata alone does not prove unmodified content. The canonical owner's own source file needs no installer metadata, but its assessed revision must still be identified.
- **Suitability:** compare the skill's workflow with local instructions,
  compatibility floors, component classes, build manifests, and CI. Confirm
  relevant checks for Zsh plugins/annexes, Go, compiled modules, documentation,
  or packaging/infrastructure as applicable. Human or agent judgment is
  required for local overrides and missing contracts; a matching file or
  language keyword is not evidence of semantic suitability.
- **Runtime evidence:** distinguish static readiness from observed discovery
  and invocation. For Copilot code review, link an authorized review's skill
  attribution when available; otherwise report invocation as unverified.
  A successful review without attribution does not establish skill use.

The approved canonical revision is the one recorded for the skill in
`knowledge/domains/agents/data/approved-skills.json`. A record that names its own `source` is approved from that repository instead of `z-shell/.github` (decisions/0037). For a repository declared in the `downstream`
section of `.github/instruction-surfaces.json`, the provenance, currency, and
local-drift dimensions are deterministic: run
`python3 automation/agents/org-routing.py check --repository z-shell/<name> --root <checkout>`
from a `z-shell/.github` clone, or read the repository's `Org Routing` check
(decisions/0031). A pinned revision other than the approved one is stale even
when the content is identical. Presence, suitability, and runtime evidence
still need the assessment above.

Report each failed dimension as missing, invalid, stale, modified, unsuitable,
or unverified with evidence and a concrete remedy. Missing, invalid, stale,
modified, or unsuitable guidance prevents a clean review-readiness result.
Unavailable source or suitability evidence must remain unverified. A local
draft is not published default-branch coverage. Report local and published
results separately, with assessed and unassessed counts.

Health evaluations only propose remediation. When installation or update is
authorized, make the scoped change and rerun these checks. Preserve existing
local changes and resolve differences before replacing an installed copy.
Policy and deterministic health tooling own this gate even when optional
skills are not selected by the runtime.

### MCP review context

During health evaluation, record whether the repository selects the `github`
baseline, `github-docs`, or no MCP profile, and why that choice fits its actual
components. Optional services are not a health prerequisite. Follow
[integration guidance](../../../.github/instructions/agents/tool-integration.instructions.md#copilot-hosted-review)
for hosted compatibility and tool selection. Keep these evidence dimensions
separate:

- **Configured:** identify the assessed repository revision, profile, runtime,
  observation time, and source of the active hosted setting evidence. Record
  server identities, selected tools, authentication mode and access boundaries
  without credential values. A local declaration or a documented default alone
  leaves actual hosted configuration unverified.
- **Discovered:** cite startup or `tools/list` evidence for that configuration,
  including the tools' read-only annotations. A configured server may fail to
  start, authenticate, or expose tools eligible for review.
- **Invoked:** cite an authorized review session or comment attribution showing
  the server and tool used, reviewed head revision, and observed time. A passing
  review or successful startup alone does not establish invocation or relevance.

Bind observations to the exact configuration revision or a digest of its
sanitized snapshot, plus the reviewed commit where applicable. Refresh evidence
after configuration, server version, access, or relevant repository changes;
an earlier successful call cannot verify the changed setup. Record unavailable
settings, logs, annotations, or calls as unverified, and preserve conflicting
evidence rather than inferring a pass from a local file.

Report this separately from skill readiness. Absence of optional MCP services
does not fail repository health. A selected profile whose required context is
unavailable has an explicit context gap, not a verified tailored review.
Keep administrative settings and private session evidence in the private
handoff; publish only authorized, public-safe conclusions.

Pilot the GitHub profile in the canonical owner and a standard plugin, then
documentation lookup in the wiki. Verify useful context retrieval on a
representative authorized review before wider configuration. A health
evaluation does not authorize settings changes, credentials, server installs,
or new hosted reviews.

### Install or update after authorization

The canonical source is this repository's [code-review skill](../../../.github/skills/code-review/SKILL.md). Shared review criteria are authored once in [the code-review knowledge source](code-review.md) and generated into both [code-review.instructions.md](../../../.github/instructions/quality/code-review.instructions.md) and the skill's bundled [criteria reference](../../../.github/skills/code-review/references/criteria.md), so a vendored skill carries the criteria at its pinned revision. The portable skill discovers local contracts; it does not require this repository to be a sibling checkout.

Verify `gh version` and `gh skill install --help`. After the canonical skill is
published at an approved immutable commit, run from the target repository:

```text
gh skill install z-shell/.github .github/skills/code-review --pin <approved-commit-sha> --dir .github/skills
```

Replace the placeholder with the full approved commit SHA. Do not rely on the
agent's default destination, which can resolve to `.agents/skills`. Preserve
the native installer's GitHub source metadata. Avoid `--force` while a local
copy has unexplained differences. Do not publish `--from-local` metadata
containing a maintainer's local paths. Before publication, byte-identical local
draft copies may be evaluated as drafts without inventing source metadata or
claiming a remote installation. See the
[GitHub CLI installation manual](https://cli.github.com/manual/gh_skill_install).

For updates, compare the recorded source revision and actual installed files
against the currently approved canonical revision explicitly;
`automation/agents/org-routing.py check` does this for declared repositories. `gh skill update
--dry-run` skips pinned skills, so its output cannot establish currency. Once
the differences and update scope are approved, reinstall at the new approved
commit and verify the resulting content and metadata. An unchanged repeated
installation should leave no diff. See the
[GitHub CLI update manual](https://cli.github.com/manual/gh_skill_update).

Advancing the approved revision is a reviewed change to `knowledge/domains/agents/data/approved-skills.json` in this repository: set the new commit and, for a skill with files besides `SKILL.md`, record each of them under `resources` with its Git blob id at that commit. Run `python3 automation/agents/org-routing.py verify-approved` to confirm the digest, file list and resource blob ids, and merge it before any downstream repository re-pins. `verify-approved` requires the approved commit to be an ancestor of the checked-out `HEAD`, and a squash merge rewrites a pull request's commits, so a skill change and its approval land in separate pull requests. Each downstream re-pin is then a separately authorized change in that repository.

Pilot changes in the canonical owner, a standard plugin, and a documentation
repository before wider delivery. Exercise representative review requests
against each repository's own checks. Triggering a hosted Copilot review needs
separate authorization; inspect attribution afterward rather than inferring
use from skill presence. See
[GitHub's review guidance](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review).

## Read-only coverage report

Run `python3 automation/agents/org_policy_report.py coverage --live` from a current, reviewed organization checkout. It uses read-only `gh api` calls, fully paginates the repository inventory, and observes declared active consumers at immutable default-branch commits. It reports generated routing-block currency, workflow caller references, approved skill pins and content, resource inventory, and effective ruleset-required check names. It performs no installation, dispatch, tracker write, repository edit or settings change. Keep output containing private repositories private.

For an offline report, save the REST repository inventory as a JSON array (or the page arrays produced by `gh api --paginate --slurp`) and pass `coverage --inventory inventory.json`. An optional `--checkouts checkouts.json` maps full repository names to local checkout paths and runs the local routing verifier. Local validation and published observations remain separate. The report includes its canonical source revision and observation time; record the collection time of an offline inventory separately.

Read findings and evidence gaps even when the command exits zero: zero means the report was produced, not that organization compliance passed. Archived repositories are listed as excluded; undeclared repositories, maintained forks and declared repositories missing from the inventory remain explicit coverage gaps. Only declared active consumers receive detailed file observations. A truncated tree or failed API request produces unavailable evidence, never a passing result. Inventory visibility depends on the caller's access.

Caller references do not prove trigger eligibility or successful CI. Ruleset-required checks describe the observed default branch. Classic branch protection, bypass settings and other integration branches require separate checks; assess Zi's `next` separately. Runtime discovery, skill invocation and repository-specific semantic suitability remain unverified or unassessed until the earlier review-readiness procedure supplies evidence. A multi-file skill's content is reported current only when its approved record pins every resource by Git blob id and each published blob matches; without those pins it remains unverified. Compare observed workflow pins with the intended approved tooling revision independently.

Use this report as input to the existing weekly-review pilot (#412) and recurring-operations coordination (#485). A schedule is optional and needs its own authorization; evaluate the first three drafts before expanding cadence or scope. Deterministic PR checks remain the immediate change gate. New settings enforcement follows #478 after a caller has a verified successful run; #665 remains the adoption owner.

## Prompt template

```text
Using GitHub tools, review the last 7 days across the z-shell organization.

- summarize new issues by repository
- flag regressions, security-sensitive issues, and release blockers
- list PRs waiting for review for more than 3 days
- identify repeated patterns across repositories
- suggest a prioritized maintainer action list
- when assessing repository health, report review-skill readiness, source drift,
  repository suitability, coverage gaps, and runtime invocation evidence

Output sections:
1. Urgent
2. Needs review
3. Cross-repo patterns
4. Suggested follow-ups

Do not act. Draft only.
```

## Follow-up discipline

- If the review suggests a non-trivial new task, propose a GitHub issue in the owning repository.
- If an item is already tracked, link it instead of duplicating it.
- If the review exposes a recurring rule or process gap, propose a `PATTERNS.md`, ADR, or runbook update.

## See also

- `runbooks/triage.md`
- `runbooks/adr.md`
- `.github/AGENT_MEMORY.md`
