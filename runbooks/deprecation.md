# Runbook — Deprecation and Sunset

How to retire a plugin, annex, package, or other artifact without breaking the
users and tooling that depend on it.

**Hard rule:** never delete a published artifact or break an install path
silently. Announce, provide a migration, then archive — in that order.

## When to use this

Use this when an artifact is no longer maintained or has been superseded:

- a plugin/annex replaced by another or folded into core
- a package no longer published
- a repo that should become read-only

Quiet repositories are not abandoned by default. Low issue volume, few commits,
or a stable done state are signals to review maintainer intent, consumer usage,
and replacement availability; they are not enough on their own to deprecate or
archive a project.

Do not use this for routine workflow-hygiene cleanup (removing a stale CI
workflow) — that is ordinary maintenance, kept separate from release semantics.

## Step 1 — Decide and record

1. Confirm the artifact's class (ADR-0007), what consumes it, and whether it is
   intentionally stable, actively replaced, or genuinely unmaintained. Use issue
   activity as context, not as the decision.
2. Identify maintainer intent and replacement availability. If maintainers intend
   the project to remain stable, record that state instead of starting the
   sunset process.
3. File a tracker issue describing the deprecation, the replacement (if any), and
   the migration path. If the decision is non-obvious or cross-repo, draft an ADR
   (`runbooks/adr.md`).
4. Identify every public dependency: the GitHub repository, `zi` ice,
   meta-plugin labels (`z-a-meta-plugins`), wiki references, package records,
   and other documented install paths.

## Step 2 — Announce

- Add a deprecation notice to the repo README and the wiki page, stating the
  status, the replacement, and the timeline.
- Where the artifact loads, prefer a non-fatal warning over a hard break.
- Label the tracker issue and link the announcement.

## Step 3 — Provide a migration

- Document the replacement and the exact steps to switch (new label, new repo,
  new ice).
- Keep the old install path working through a transition window; do not remove it
  the same day you announce.
- For git-consumed artifacts (class 3), the consumable ref must keep resolving
  until the window closes.

## Step 4 — Sunset

After the transition window:

- For a versioned artifact (class 2), cut a final tagged release noting end of
  support; do not yank prior tags.
- Remove the artifact from meta-plugin maps, wiki ecosystem listings, package
  indexes, and public install documentation as applicable.
- Archive the GitHub repository (read-only) rather than deleting it, so existing
  references and history remain resolvable.
- Treat any maintainer-local catalog cleanup as a separate local operation
  governed by that tool's own instructions.
- Close the tracker issue with the final state and links.

## Anti-patterns

- deleting a repo or yanking published tags, breaking existing installs
- removing an artifact from catalogs while it is still referenced elsewhere
- announcing and removing in the same change with no transition window
- mixing deprecation with unrelated release automation work

## See also

- `decisions/0007-release-publication-flow.md`
- `decisions/0008-branching-model.md`
- `runbooks/release.md`
- `runbooks/triage.md`
