---
description: "Testing and CI expectations for z-shell repositories, by repository class"
applyTo: "**"
---

# Testing Instructions

How much to test, and what CI to require, depends on the repository's class.
This operationalizes `decisions/0009-testing-ci-strategy.md`; the class
definitions come from `decisions/0007-release-publication-flow.md`.

## Identify the class first

| Class | Repos                                        | What it is                     |
| ----- | -------------------------------------------- | ------------------------------ |
| 1     | `wiki`, `src`, `zd`                          | Continuously deployed artifact |
| 2     | `zunit`, `zsh-lint`, `zpmod`, packaged `zsh` | Versioned tool/package         |
| 3     | `zi`, most plugins/annexes                   | Git-consumed source            |
| 4     | `.github`                                    | Meta/infrastructure            |

## Baseline (every repo)

- Workflows follow org conventions: SHA-pinned actions, top-level
  least-privilege `permissions:`, `concurrency:` on push/PR, no-emoji workflow/
  job `name:` (ADR-0005), kebab-case filenames.
- Zsh sources pass `zsh -n` and `zcompile`.
- Conventional Commits, PR-title validation, and the disallowed-trailer rule
  are target gates. Enforcement is repository-scoped. Verify the owning
  repository's live caller and required-check or ruleset configuration before
  relying on CI. Where no verified gate exists, authors and reviewers remain
  responsible.

## By class

- **Class 1, deployed:** the build must pass on pull requests into `main` and
  on the merged `main` commit before deploy. Wiki: ESLint + Stylelint +
  production build. `zd`: Docker build matrix.
  `src`: installer/loader validation. Add CodeQL where a supported language exists.
- **Class 2, versioned tools:** a **full functional suite is required on the
  exact tag commit and gates release publication**. ZUnit for Zsh tools;
  `go test` for the `zsh-lint` Go CLI; the repository-defined full suite for
  `zpmod`. Never cut a `vX.Y.Z` tag from a red commit.
- **Class 3, git-consumed:** **validation-only as the required organization
  gate.** Run existing repository-owned tests and add regression coverage when
  behavior changes, but do not impose a release suite or coverage gate. A
  maintained plugin also proves its Standard 2 load surface and exact lifecycle
  contract in a clean process.
- **Class 4 — meta:** baseline plus workflow/markdown linting.

## Coverage

Coverage is **observed, not gated**, unless a class-2 tool sets its own threshold.
Do not add an org-wide coverage number.

## Writing Zsh tests

- Use ZUnit for Zsh unit tests and keep one behavior per test. Standalone Zsh
  integration or system tests are also valid when they exercise boundaries that
  do not fit a unit test.
- Test plugins by sourcing them in a clean Zsh session; there is no build step.
- Before testing autoloaded functions, clear or rebuild inherited `FPATH` and
  `fpath` from the subject checkout. A same-named entry from another worktree
  or installation can make tests exercise stale code.
- Prime lifecycle observers before the baseline. Compare functions, parameters
  and attributes, aliases, options, traps, modules, hooks, widgets, bindings,
  styles, `path`, and `fpath` without printing captured values.
- Assert the documented load allowlist, harmless repeated source, cleanup after
  partial failure, hostile caller options, non-interactive behavior, and exact
  unload restoration.
- Use ownership-aware cleanup assertions: restore the pre-load value only when
  the user did not change the installed value, otherwise preserve the user's
  newer state.

## Required checks

Mark the class-appropriate checks as required on the integration branch
(`main`, or `zi`'s named `next` exception per ADR-0019). Class-3 repositories
require the baseline; class-2 repositories additionally re-run the functional
suite against the exact commit before a release tag is published.

For `zi`, ordinary pull requests validate against `next`; the promotion pull
request into `main` runs the full stable-branch check set on its exact head SHA.

Organization templates must pin zsh-lint and ZUnit to exact commits belonging
to published releases. Do not use mutable branches, tags, or unreleased pull
request commits as a required organization gate.

## See also

- `decisions/0009-testing-ci-strategy.md`
- `decisions/0007-release-publication-flow.md`
- `.github/instructions/github-actions-ci-cd-best-practices.instructions.md`
- `.github/instructions/shell.instructions.md`
