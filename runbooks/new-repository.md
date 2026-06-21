# Runbook — New Repository Bootstrap

How to create a new z-shell plugin, annex, or module repository without copying
unreviewed files from an existing project.

**Hard rule:** keep organization-wide instructions, workflows, and issue
metadata centralized. Add child-repository files only when the repository needs
project-specific behavior.

## Step 1 — Classify and record the repository

1. Open a tracker issue describing the artifact, owner, consumers, and release
   class from `runbooks/release.md`.
2. Choose the repository name:
   - plugin: `zsh-<name>`
   - annex: `z-a-<name>`
   - compiled module: a short descriptive name
3. Add the clone to the private meta-workspace `.gitmodules` and
   `workspace/repos.yml`. Do not put local paths, credentials, or machine facts
   in the public repository.
4. Apply canonical labels via `runbooks/labels.md` and configure task tracking
   through `runbooks/project-tracker.md`.

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

Use the organization-approved license for the artifact. For a Zsh plugin,
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

Follow the entry-point, `ZERO`, `Plugins`, guarded `fpath`, and unload patterns
in `PATTERNS.md` and the Z-Shell Plugin Standard. The unload function must
reverse plugin-owned side effects.

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
4. Add `renovate.json` only for a repository-specific exception such as a
   `next` target branch.
5. Do not add `.github/dependabot.yml` for routine version updates.

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
- `runbooks/dependency-management.md`
- `runbooks/labels.md`
- `runbooks/project-tracker.md`
- `runbooks/release.md`
- `runbooks/triage.md`
