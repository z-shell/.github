# 27. Adopt One Canonical Repository README Location and Shared Structure

- **Status:** PROPOSED
- **Date:** 2026-09-19
- **Deciders:** TBD
- **Supersedes:** None
- **Superseded by:** None

## Context

Organization README guidance applied the shared template only to Zsh plugins. Annexes, compiled modules, tools, and environment repositories had no required route to the template, even though they need the same high-level information and accessible visual hierarchy. The optional `create-readme` skill described several archetypes, but mandatory organization policy cannot rely on an optional skill or one runtime.

Repository README placement was also implicit. Maintained repositories used `docs/README.md`, `.github/README.md`, or a root `README.md` without a written selection rule. Multiple files would introduce GitHub's location precedence, while moving a README changes every relative link. A single explicit location avoids both ambiguity and duplicate maintenance.

The bootstrap runbook separately required Prettier's `proseWrap: never`. That setting joins the separate quoted lines used by GitHub alerts, so the README template's callouts can become ordinary blockquotes. Prettier's default `preserve` behavior keeps the author-controlled line structure.

Issue [#624](https://github.com/z-shell/.github/issues/624) records the concrete annex failure and the conflicting bootstrap guidance.

## Decision

1. Every maintained repository has exactly one repository landing README.
2. Use `docs/README.md` when `docs/` already exists, otherwise `.github/README.md` when `.github/` exists, and otherwise `README.md` in the repository root. Do not create `docs/` solely to host the README.
3. Adjust relative links for the selected location, including links to the repository license and repository-owned assets.
4. When creating a repository README or substantially restructuring one, start from `templates/readme/zsh-plugin.md`. Focused corrections do not require a full rewrite.
5. The shared template owns the common information order and accessible visual hierarchy. Zsh plugins may use its body directly. Annexes, compiled modules, tools, and environment or meta repositories adapt plugin-specific headings, examples, links, and checklist items to their archetype.
6. Plugin Standard, Zi, plugin-manager, Zsh-manual, and shell-lifecycle requirements apply only where the repository archetype uses them. Every repository links the authoritative documentation for its actual user-facing surface.
7. Repositories that use Prettier for Markdown retain the default `proseWrap: preserve` behavior unless a separately documented repository requirement says otherwise. GitHub alert markers and bodies remain on separate quoted lines.
8. Required documentation guidance routes this policy to every supported runtime. Optional skills may provide a detailed authoring workflow but do not own the mandatory rule.

## Consequences

### Positive

- Every supported runtime receives the README template and placement rule.
- One README avoids conflicting copies and makes relative-link ownership explicit.
- Repository archetypes share a recognizable information order without making false plugin claims.
- Default Markdown wrapping preserves both intentional prose layout and valid GitHub alert syntax.

### Costs and risks

- A README under `docs/` or `.github/` is less visible in the repository file tree than a root README, although GitHub recognizes and renders all three supported locations.
- Moving an existing README requires checking every relative link and repository-owned asset path.
- A plugin-first template requires deliberate adaptation for non-plugin archetypes. Regression tests can enforce conditional language but cannot prove that a generated README describes its implementation accurately.
- The organization preference differs from GitHub's precedence order when multiple READMEs exist. The one-README rule makes that precedence irrelevant, but repositories that already contain duplicates need a deliberate reconciliation rather than an automatic deletion.

## Alternatives considered

1. **Always use a root README.** Rejected because maintained repositories already keep tightly coupled user documentation under `docs/`, and the organization wants the landing page beside that content when the directory exists.
2. **Follow GitHub's `.github`, root, then `docs` precedence.** Rejected because precedence resolves rendering only after duplicates exist; it does not prevent conflicting content or make the organization preference explicit.
3. **Maintain separate complete templates for every archetype.** Rejected because the common information order, accessibility rules, badges, verification, support, and contribution sections would drift across copies.
4. **Keep the template plugin-only and rely on the optional skill for other archetypes.** Rejected because runtimes that do not load the skill would continue to miss the mandatory organization guidance.
5. **Keep `proseWrap: never` and stop using GitHub alerts.** Rejected because alerts communicate high-impact prerequisites and warnings accessibly, while `preserve` supports both alerts and one-paragraph-per-line prose.

## References

- [z-shell/.github#624](https://github.com/z-shell/.github/issues/624)
- [z-shell/.github#634](https://github.com/z-shell/.github/pull/634)
- [GitHub README locations](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes)
- [GitHub alert syntax](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#alerts)
- [Prettier prose-wrap options](https://prettier.io/docs/options#prose-wrap)
- `runbooks/instruction-update.md`
- `.github/instructions/documentation.instructions.md`
- `.github/skills/create-readme/SKILL.md`
- `templates/readme/zsh-plugin.md`
