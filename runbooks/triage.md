# Runbook — Triage

How to classify, prioritize, and respond to issues and pull requests across the z-shell organization.

**Hard rule:** LLM agents draft; humans apply labels, post comments, and close items.

## When triage happens

- **New issue or PR:** within 48 hours, sooner for active repositories such as `zi` and `wiki`
- **Weekly sweep:** review anything missed during the week
- **Ad hoc:** immediately for security, regression, release-blocking, or cross-repo issues

## Step 1 — Read and classify

For each item, answer:

1. What kind of work is this: bug, feature, docs, question, maintenance, or meta?
2. What area does it touch: `zi`, plugin, annex, docs, CI, release, org infrastructure, or unknown?
3. Is it a real bug, a design request, or a configuration/support question?
4. Has this shown up before in this repository or elsewhere in the org?

If classification takes more than a few minutes, mark it for investigation and move on.

## Step 2 — Apply the canonical labels

The organization label set in `lib/labels.yml` is the source of truth. Apply at least one work-type label and one area label when the area is known.

### Work type

| Intent                  | Label              |
| ----------------------- | ------------------ |
| bug                     | `type:bug`         |
| feature request         | `type:feature`     |
| documentation only      | `type:docs`        |
| maintenance or org work | `type:maintenance` |
| support or usage        | `type:question`    |
| membership              | `type:membership`  |
| agent handoff           | `type:handoff`     |

### Area / shape

| Area                 | Label               |
| -------------------- | ------------------- |
| `zi` core            | `area:zi`           |
| plugin               | `area:plugin`       |
| annex                | `area:annex`        |
| package              | `area:package`      |
| docs                 | `area:docs`         |
| CI or GitHub Actions | `area:ci`           |
| dependencies         | `area:dependencies` |
| release              | `area:release`      |
| org infrastructure   | `area:meta`         |

### Severity / modifiers

| Meaning                | Label              |
| ---------------------- | ------------------ |
| needs initial review   | `status:triage`    |
| blocked                | `status:blocked`   |
| waiting on more detail | `needs-info`       |
| regression             | `regression`       |
| high priority          | `priority:high`    |
| breaking change        | `breaking-change`  |
| security-sensitive     | `security`         |
| performance-sensitive  | `performance`      |
| good first issue       | `good first issue` |
| help wanted            | `help wanted`      |
| invalid                | `invalid`          |
| duplicate              | `duplicate`        |
| not planned            | `wontfix`          |

## Step 3 — Cross-reference

Before responding:

1. Search the same repository for related closed issues or PRs.
2. Search the organization for the same symptom or pattern.
3. Check `decisions/` for relevant ADRs.
4. Check `PATTERNS.md` and the wiki when a known implementation pattern may answer the question.

If the issue conflicts with an accepted ADR or established pattern, say so directly and link it.

## Step 4 — Draft the first response

The first response should:

1. acknowledge the report or PR
2. restate the issue in one sentence
3. give exactly one concrete next step

Typical next steps:

- reproduced and tracking
- needs more detail
- duplicate of another issue
- by design, with documentation or ADR link
- PR welcome, with guidance

Do not promise delivery dates.

## Step 5 — Decide whether it belongs on the tracker

Add the work to Linear when it:

- crosses repositories
- blocks a release
- has security impact
- has strategic or roadmap significance

Linear's native GitHub integration will automatically ingest tracking issues based on configuration. Do not apply broad sync to ordinary single-repository bugs, questions, or cleanup tasks. See `runbooks/project-tracker.md`.

In Linear, populate:

- `Priority`: `Low`, `Medium`, or `High`
- `Estimate`: e.g. `1`, `2`, `3`
- `Project`: Assign to relevant strategic project
- `Status`: `Triage`, `Todo`, `In Progress`, `In Review`, or `Done`

## Step 6 — Close with an explicit reason

When closing an issue or PR, always leave the reason in the thread:

- resolved, with the fixing PR or commit
- duplicate, with the canonical issue
- wontfix, with the reasoning and ADR link where applicable
- invalid, with a respectful explanation

Avoid silent closures and bulk cleanup without context.

## Special cases

### Security reports

Do not handle exploit details publicly.

1. Mark the item with `security`.
2. Ask the reporter to continue privately via the security policy.
3. Remove or hide exploit details when appropriate.
4. Continue investigation off the public thread.

### New-contributor pull requests

- lower the friction
- be specific about requested changes
- prefer mentoring and takeover help over vague "needs work" feedback

## Anti-patterns

- labels with no explanation
- bulk stale closures with no human context
- demanding excessive reproduction steps for obvious bugs
- leaving `needs investigation` items to rot forever

## See also

- `AGENTS.md`
- `.github/AGENT_MEMORY.md`
- `PATTERNS.md`
- `decisions/`
- `runbooks/labels.md`
- `runbooks/project-tracker.md`
