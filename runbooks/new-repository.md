# Runbook — New Repository Bootstrap

How to create a new z-shell plugin, annex, or module repository without copying
unreviewed files from an existing project.

**Hard rule:** keep organization-wide instructions, workflows, and issue
metadata centralized. Add child-repository files only when the repository needs
project-specific behavior.

## Step 1 — Classify and record the repository

1. Open an owning issue describing the artifact, owner, and consumers.
2. Choose the repository name:
   - plugin: `zsh-<name>`
   - annex: `z-a-<name>`
   - compiled module: a short descriptive name
3. Record the owning issue, repository classification, canonical labels, and
   release class from `runbooks/release.md` in GitHub-visible project state.
4. Apply canonical labels via `runbooks/labels.md` and configure task tracking
   through `runbooks/project-tracker.md`.

Any maintainer-local inventory update is a separate local operation governed by
that tool's own instructions; it is not a public bootstrap dependency.

## Step 2 — Create the common repository envelope

Every repository starts with:

```text
LICENSE
README.md
.editorconfig
.gitignore
.github/
  workflows/
```

Select the license deliberately and record the choice on the owning issue from
Step 1. Do not leave it to whatever the repository template happens to create;
that is how the organization accumulated six differing licenses against an
intent nobody had written down.

Per [`decisions/0017-licensing-standard-by-provenance.md`](../decisions/0017-licensing-standard-by-provenance.md):

| The repository is                                     | License                        |
| ----------------------------------------------------- | ------------------------------ |
| organization-authored, not loaded into a user's shell | GPL-3                          |
| organization-authored, sourced into a user's shell    | permissive (MIT), deliberately |
| a fork or repackaging of third-party work             | upstream license, unchanged    |

A fork never gets relicensed: the organization does not hold the copyright.
For organization-authored code, note that the choice is effectively permanent,
since a license grant already published cannot be revoked and a later change
reaches only future releases.

For a Zsh plugin,
start from [`templates/readme/zsh-plugin.md`](../templates/readme/zsh-plugin.md).
The initial README must state the purpose, features, install path, supported
shell/runtime, public configuration, lifecycle behavior, verification command,
release model, and wiki link. Preserve the template's accessible visual
hierarchy, but replace its placeholders and omit optional sections that do not
serve the plugin.

Do not copy generic `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/agents/`, or
`.github/instructions/` files into child repositories. Link to the organization
guidance when a short project-specific `AGENTS.md` is genuinely required.

Use organization issue and pull-request templates by default. Add a child
template only when the repository has a specific intake field that the shared
template cannot express.

## Step 3 — Add the artifact structure

### Plugin

```text
zsh-<name>.plugin.zsh
functions/                 # only when autoloaded functions are needed
lib/                       # only when sourced helpers are needed
docs/                      # short repository-local usage only
```

Follow the entry-point, `ZERO`, namespaced state, ownership-tracked `fpath`, and
unload patterns in `PATTERNS.md` and the
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard).
Official Zsh documentation remains authoritative for shell semantics. Treat
`PMSPEC` and similar manager capabilities as optional profiles rather than
portable requirements. Namespace plugin-owned state, scope option changes, keep
network activity out of the load path, and reverse only plugin-owned side
effects during unload.

### Annex

```text
z-a-<name>.plugin.zsh
functions/
docs/                      # short repository-local usage only
```

Keep annex handlers in `functions/`, start them with strict Zsh emulation, and
register only implemented handlers. Document durable ecosystem usage in the
wiki and link to it from the repository.

### Compiled module

Compiled modules require a design issue before scaffolding because toolchains
and loader contracts vary. The issue must define:

- source and generated-file layout
- supported Zsh versions and platforms
- build and test commands
- install and load path
- release artifact and semantic-tag policy

Do not invent a reusable module template from a single implementation. Add one
to this repository only after the shape is verified in multiple module repos.

## Step 4 — Install CI from canonical templates

Start from the organization workflow templates:

- `workflow-templates/zsh-ci.yml` for Zsh syntax and smoke validation
- `workflow-templates/trunk.yml` for Trunk Code Quality

Follow `PATTERNS.md`: pin action and reusable-workflow references to immutable
commit SHAs with readable version or branch comments. Declare top-level
permissions and concurrency for push and pull-request workflows.

Add release automation only when the release class requires it. Plugins and
annexes consumed directly from Git usually need validation only.

## Step 5 — Configure dependency automation

Follow `runbooks/dependency-management.md`:

1. Grant the Renovate GitHub App access to the repository.
2. Confirm Renovate discovers `z-shell/.github/renovate-config.json`.
3. Enable the dependency graph, Dependabot alerts, and Dependabot security
   updates in GitHub settings.
4. Add `.github/renovate.json` only for a repository-specific exception such
   as a `next` target branch. If `decisions/0008-branching-model.md` assigns
   this repository the `next` to `main` model, this exception is mandatory,
   not optional. See `runbooks/branch-protection.md`.
5. Do not add `.github/dependabot.yml` for routine version updates.

## Step 5a — Provision branch rulesets

If this repository uses the `next` → `main` model
(`decisions/0008-branching-model.md`), follow `runbooks/branch-protection.md`
in full before opening the bootstrap pull request. Trunk-on-`main`
repositories still need a `main` ruleset, but can skip the `next`-specific
items (the guard workflow, `.github/renovate.json` override).

## Step 6 — Verify before publication

Before opening the bootstrap pull request:

1. Run `git diff --check`.
2. Parse every workflow YAML file.
3. Run the repository's syntax and smoke checks.
4. Confirm action references are immutable SHAs.
5. Confirm no generic AI orchestration files, secrets, local paths, or generated
   output were added.
6. Link the tracker issue and leave an `Agent handoff` comment for deferred
   template or release work.

## Deferred scaffold assets

The organization maintains focused templates such as
`templates/readme/zsh-plugin.md`, but does not maintain a generated repository
source tree. Create dedicated template repositories only through separate
tracked issues after repeated bootstrap work proves a stable full-repository
scaffold.

Reusable screenshot and terminal-demo generation is tracked separately in
[Linear ZSH-18](https://linear.app/ss-o/issue/ZSH-18/automate-readme-screenshots-and-terminal-demos-for-zsh-plugins).

## See also

- `AGENTS.md`
- `PATTERNS.md`
- `runbooks/branch-protection.md`
- `runbooks/dependency-management.md`
- `runbooks/labels.md`
- `runbooks/project-tracker.md`
- `runbooks/release.md`
- `runbooks/triage.md`
