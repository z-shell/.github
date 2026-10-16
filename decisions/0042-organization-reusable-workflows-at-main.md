# 42. Reference Organization Reusable Workflows at main

- **Status:** ACCEPTED
- **Date:** 2026-10-16
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

The workflow contract required every `uses:` reference, including the organization's own reusable workflows in `z-shell/.github/.github/workflows/`, to be pinned to a full commit SHA, with an interim `# main` comment until those workflows had releases. Callers therefore had to change their pin to receive any change to a shared workflow. With shared workflows used across the organization's repositories, every change to one meant a pull request in each calling repository, and pins drifted apart in the meantime: callers of the same workflow ran different revisions of it.

The starter templates in `workflow-templates/` already reference the shared workflows at `@main`, so new repositories started outside the written rule.

The shared workflows live in `z-shell/.github`, whose `main` is protected and changes only through reviewed pull requests. Third-party actions are outside that review.

## Decision

1. Callers reference reusable workflows from `z-shell/.github/.github/workflows/` at `@main`. A change merged to `z-shell/.github` `main` reaches every caller on its next run.
2. Every other remote reference stays pinned to a full 40-character commit SHA with its release comment: third-party actions, third-party reusable workflows, and organization actions under `z-shell/.github/actions/`.
3. Existing full-SHA pins of organization reusable workflows remain valid until each caller moves to `@main` in its own reviewed change. Such a pin must still name a commit on the default branch ([#774](https://github.com/z-shell/.github/issues/774)).
4. The shared pinact template accepts both an exact `main` ref and a full SHA for organization reusable workflows only.

## Consequences

- A shared workflow change needs one reviewed pull request in `z-shell/.github` instead of one in each calling repository, and all callers run the same revision.
- A defect merged to a shared workflow reaches every caller at once. Review on `z-shell/.github` is the control for that risk; a caller that must freeze a revision can still pin a default-branch SHA under point 3.
- Changing a shared workflow's inputs, outputs or required permissions affects every caller on its next run, so such changes need the same care as an interface change: keep them backward compatible or coordinate the callers first.
- Moving existing callers from SHA pins to `@main` is separate, per-repository work.

## Acceptance

Accepted by ss-o on 2026-10-16.

## Alternatives considered

1. Keep SHA pins and let Renovate propose digest updates: keeps each caller on reviewed code, but still produces a pull request per repository per shared change, and callers diverge until each one merges.
2. Versioned workflow releases (tags) referenced by SHA with a release comment: makes revisions explicit, but adds a release step to every shared change and still needs a pin update in each caller.

## References

- [Workflow contract: Action Pinning](../knowledge/domains/ci/workflow-contract.md).
- [ADR-0009](0009-testing-ci-strategy.md), which defers workflow conventions to the contract.
