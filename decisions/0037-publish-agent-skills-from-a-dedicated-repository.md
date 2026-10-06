# 37. Publish User and Developer Agent Skills From z-shell/agent-skills

- **Status:** PROPOSED
- **Date:** 2026-10-06
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

`z-shell/.github` holds eleven agent skills in `.github/skills/`. Six of them carry out organization process and sit beside the runbooks they route to: `code-review`, `pull-request`, `project-tracker`, `github-issues`, `review-project-learning` and `create-readme`. The other five help people use or develop z-shell software: `zi-install`, `zsh-plugin`, `zunit-test`, `zd-test` and `zsh-manual-research`. Only the first group belongs with organization policy.

Projects reach these skills today only by vendoring a pinned copy with `gh skill install --pin`, verified against `knowledge/domains/agents/data/approved-skills.json` under ADR-0031. Individual users of Claude Code and Codex have no install route. Both runtimes install skills from plugin marketplaces, which need a repository laid out as a plugin with generated manifests.

`automation/agents/org-routing.py` accepts only `z-shell/.github` as the source of an approved skill, so no project can pin a skill published anywhere else.

Some of the five names also do not explain themselves. `zd-test` names a test, although zd is an execution environment for runtime checks, ABI checks and benchmarks. The [skill naming and scope rules](../knowledge/domains/agents/skill-naming.md) now define one skill per subject, with a `<subject>-<action>` skill only for a part with a different invocation mode, authority or audience.

## Decision

1. **A public repository, `z-shell/agent-skills`, owns the user and developer skills.** It starts with one plugin, `z-shell`, containing the five skills above. Organization process skills stay in `z-shell/.github` beside their runbooks. A separate user plugin waits until the user side has at least two maintained skills.
2. **One hand-edited catalog generates every manifest.** `catalog.json` holds plugin names, versions, descriptions and skill membership. A generator writes the Agent Skills `plugin.json`, the Claude `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, and its `--check` mode runs in CI with `claude plugin validate . --strict` and a link check. Every release bumps the catalog version, because Claude refreshes an installed plugin only when its version changes.
3. **Each skill belongs to exactly one plugin**, as real files under `plugins/<plugin>/skills/<name>/`. Codex reads one skills directory per plugin and does not keep symbolic links. Drafts live under `in-progress/`, outside every manifest.
4. **Every skill declares one invocation mode.** A user-invoked skill sets `disable-model-invocation: true` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`; a model-invoked skill sets neither. A skill reaches another skill by name, never by a `../` path.
5. **Skills move under names that follow the naming rules**: `zunit-test` becomes `zunit`, `zd-test` becomes `zd`, and `zsh-plugin` keeps its name but covers maintaining plugins as well as creating them, becoming model-invoked. `zi-install` and `zsh-manual-research` keep their names. The generator check enforces the name format and the paired invocation flags.
6. **Approved skills name their source per skill.** `approved-skills.json` keeps `z-shell/.github` as the default source and lets a skill record a different approved repository and path. `org-routing.py` accepts only sources on its allowlist, checks vendored copies against their own source's installer metadata, and verifies an external revision only against a checkout of that source. This change lands before any project pin names the new repository.
7. **Two install routes, never both for one skill in one project.** Projects that need a skill for hosted agents keep a pinned vendored copy under `.github/skills/`, approved and checked as today. Individuals install the plugin from the marketplace. A project using both routes would install the same skill twice.
8. **Skills move one at a time.** For each skill: add it to `z-shell/agent-skills`, approve its revision, re-pin each vendoring project (`z-shell/src` vendors `zi-install`), then remove the old copy and its instruction surfaces here. The previous approved revision stays recorded for rollback until the re-pin is verified.

## Consequences

Users get a supported install route for the z-shell skills in Claude Code and Codex, and `z-shell/.github` keeps only organization process. Names chosen under the naming rules land once, during a move that re-pins every consumer anyway.

The cost is a second repository with its own CI, release procedure and generator, and an approved-skills format with a per-skill source that `org-routing.py`, its tests and its CI must handle. Verifying an external approved revision needs a checkout of that repository, so CI for `verify-approved` gains a second checkout once the first external skill is approved. Plugin installs, Codex marketplace installs and project re-pins each need their own verification; a valid manifest does not prove an install works.

## Alternatives considered

1. **Keep every skill in `z-shell/.github` and add marketplace manifests there.** Rejected: a plugin built from the organization repository would ship or have to filter out process skills, and Codex takes one skills directory per plugin.
2. **Two plugins at launch, one for users and one for developers.** Deferred: the user side has one skill, `zi-install`, so a second plugin adds manifests and releases with no consumer.
3. **A private companion repository for internal skills.** Rejected: private skills already have an owner in the private workspace, and no second consumer needs them.
4. **Rename the skills in place before moving them.** Rejected: every consumer would be re-pinned twice.

## References

- [Issue 741](https://github.com/z-shell/.github/issues/741), the plan and impact review.
- [Skill naming and scope rules](../knowledge/domains/agents/skill-naming.md), added in [#742](https://github.com/z-shell/.github/pull/742).
- [ADR-0031](0031-per-repository-instruction-routing-delivery.md), approved skill pins.
- [ADR-0032](0032-organization-procedures-live-once-as-public-runbooks.md), process skills as runbook routers.
- [ADR-0036](0036-central-editable-knowledge-and-generated-consumers.md), knowledge ownership independent of skill marketplaces.
- [Release runbook](../runbooks/release.md).
