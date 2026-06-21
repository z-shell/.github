---
name: create-readme
description: "Create or substantially refactor a repository README"
---

# Create README

Create an accurate, concise, and visually intentional repository landing page.

## Required workflow

1. Read the repository's source, tests, workflows, local instructions, release
   model, and linked organization policy before drafting.
2. Classify the repository. For a Zsh plugin, use
   [`templates/readme/zsh-plugin.md`](../../../templates/readme/zsh-plugin.md)
   as the canonical structure.
3. Verify every feature, setting, default, alias, lifecycle claim, command, and
   branch statement against the current implementation.
4. Lead Zsh-plugin installation guidance with Zi. Keep other manager examples
   concise and include only intentionally supported or verified paths.
5. Keep long-form ecosystem guidance in the wiki and link to it.
6. Preserve meaningful visual identity: a clear header, a restrained maintained
   badge set, accessible alt text, and an optional behavior-focused screenshot
   or demo.
7. Do not add competitor comparisons unless comparison is the document's
   explicit purpose.
8. Run repository-appropriate Markdown, link, syntax, and behavior checks before
   claiming completion.

## Visual guidance

- Use GitHub Flavored Markdown and minimal HTML where it materially improves the
  header or image sizing.
- Do not use decorative link clusters, excessive badges, emoji-heavy headings,
  or images without useful alt text.
- Prefer repository-owned assets.
- Screenshot and terminal-demo automation is tracked in Linear ZSH-18; until it
  lands, manually maintained visuals must be reviewed when documented output
  changes.

## Scope

For focused README corrections, change only the affected content. Apply the
full template when creating a repository or when the requested work is a
substantial README refactor.
