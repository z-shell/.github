---
description: "Testing and CI expectations for z-shell repositories, by repository class"
applyTo: "**"
---

# Testing Instructions

How much to test, and what CI to require, depends on the repository's class.
This operationalizes `decisions/0009-testing-ci-strategy.md`; the class
definitions come from `decisions/0007-release-publication-flow.md`.

## Identify the class first

| Class | Repos                                   | What it is                       |
| ----- | --------------------------------------- | -------------------------------- |
| 1     | `wiki`, `src`, `zd`                     | Continuously deployed artifact   |
| 2     | `zunit`, `zsh-lint`, packaged `zsh`     | Versioned tool/package           |
| 3     | `zi`, most plugins/annexes              | Git-consumed source              |
| 4     | `.github`                               | Meta/infrastructure              |

## Baseline (every repo)

- Workflows follow org conventions: SHA-pinned actions, top-level
  least-privilege `permissions:`, `concurrency:` on push/PR, no-emoji workflow/
  job `name:` (ADR-0005), kebab-case filenames.
- Zsh sources pass `zsh -n` and `zcompile`.
- Conventional Commits (ADR-0003) and the disallowed-trailer check are enforced.

## By class

- **Class 1 — deployed:** the build must pass on the development branch before
  deploy. Wiki: ESLint + Stylelint + production build. `zd`: Docker build matrix.
  `src`: installer/loader validation. Add CodeQL where a supported language exists.
- **Class 2 — versioned tools:** a **full functional suite is required and gates
  release tags**. ZUnit for Zsh tools; `go test` for the `zsh-lint` Go CLI. Never
  cut a `vX.Y.Z` tag from a red commit.
- **Class 3 — git-consumed:** **validation-only.** Baseline checks plus ZUnit
  where the plugin ships tests. No release automation, no coverage gate. The bar
  is "loads and parses cleanly."
- **Class 4 — meta:** baseline plus workflow/markdown linting.

## Coverage

Coverage is **observed, not gated**, unless a class-2 tool sets its own threshold.
Do not add an org-wide coverage number.

## Writing Zsh tests

- Use ZUnit; keep one behavior per test.
- Test by sourcing the plugin in a clean Zsh session — there is no build step.
- For annex/handler functions, assert side effects are reversed by the unload
  function (`<plugin>_plugin_unload`).

## Required checks

Mark the class-appropriate checks as required for merge to the publication branch
(`main`, or `next`→`main` per ADR-0008). Class-3 repos require the baseline;
class-2 repos additionally require the functional suite before a release tag.

## See also

- `decisions/0009-testing-ci-strategy.md`
- `decisions/0007-release-publication-flow.md`
- `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
- `.github/instructions/shell.instructions.md`
