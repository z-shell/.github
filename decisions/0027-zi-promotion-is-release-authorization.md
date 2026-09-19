# 27. Zi Promotion Is Release Authorization

- **Status:** ACCEPTED
- **Date:** 2026-09-20
- **Deciders:** ss-o
- **Supersedes:** The Zi milestone-release exception in `decisions/0007-release-publication-flow.md`
- **Superseded by:** None

## Context

Zi is consumed directly from stable `main`, but it also publishes optional semantic tags and GitHub releases for milestones. ADR-0007 originally split a milestone into two human decisions: merge a reviewed `next` to `main` promotion, then review a post-merge proposal and push a signed tag. The v2.2.0 release demonstrated that the second decision repeated the first one. The promotion pull request already identified the complete change set, exact candidate head, checks, and public impact. The proposal issue added no new evidence before asking the same maintainer to authorize the same release again.

GitHub Actions also does not start a new workflow for most events created with the repository `GITHUB_TOKEN`. An automatic publisher therefore cannot rely on pushing a tag and having the existing tag-push workflow publish the release. The workflow that creates the tag must finish the automatic publication transaction itself. Manual tags can keep the tag-push path as a recovery mechanism.

## Decision

For Zi, an eligible `next` to `main` promotion pull request is the review and authorization boundary for a milestone release:

1. A read-only pull request workflow computes the next semantic version and deterministic release notes from the commits since the latest `vX.Y.Z` tag. It displays that plan on the promotion pull request and reruns when the head changes.
2. Merging the reviewed promotion authorizes publication only when that plan identifies releasable Conventional Commits. A range with no feature, fix, performance, or breaking change is a successful no-op.
3. A privileged post-merge workflow waits until every repository-required validation workflow has succeeded on the exact promotion merge SHA. It fails closed if the merge is not an actual `next` to `main` promotion, `main` moves, validation is incomplete, or the proposed tag already exists unexpectedly.
4. That workflow creates an annotated `vX.Y.Z` tag and the corresponding idempotent GitHub release in the same transaction. The automation identity does not receive a personal SSH or signing key.
5. The existing maintainer-signed tag path remains available only for recovery and exceptional publication. Its exact-target, signature, and required-workflow verification remains mandatory.
6. Repository rules require the release-plan check on promotions and protect `v*` tags from deletion, update, and creation outside the approved automatic or recovery paths.

The promotion PR, its exact merge SHA, successful workflow runs, annotated tag, and immutable release are the audit record. Zi no longer opens a post-merge `release-proposal` issue.

Class-2 repositories are unchanged. Their reviewed annotated tag remains the publication boundary, and they may continue using the reusable `release-prepare.yml` proposal workflow.

## Consequences

### Positive

- The maintainer makes one informed release decision instead of approving the same milestone twice.
- Version and release-note review happens before the irreversible merge and tag.
- Exact-SHA validation remains stronger than merely reacting to a branch push.
- Automatic and manual recovery paths remain distinct and testable.

### Costs and risks

- Promotion review now carries publication responsibility when releasable commits exist.
- The automatic publisher needs `contents: write`, so its trigger qualification, exact-SHA checks, and workflow allowlist become security-sensitive code.
- An annotated automation tag is not cryptographically signed. Provenance instead comes from the protected promotion, GitHub Actions run, protected tag ruleset, and immutable release. Recovery tags retain maintainer signatures.
- Required workflow names are an explicit contract and must be updated when the repository changes its validation set.

## Alternatives considered

- **Keep the post-merge proposal.** Rejected because it asks for a second authorization without adding evidence unavailable on the promotion pull request.
- **Create a proposal before promotion but keep manual tagging.** Rejected because the reviewed promotion already supplies the human boundary; a second manual action only adds delay and failure modes.
- **Run publication directly on a push to `main`.** Rejected because branch identity alone does not prove a reviewed `next` promotion or that every required workflow passed on the exact merge SHA.
- **Store a signing key in Actions.** Rejected because a personal release key would expand secret handling and compromise impact without improving the reviewed-promotion boundary.

## References

- [Organization issue #644](https://github.com/z-shell/.github/issues/644)
- [Zi implementation issue #564](https://github.com/z-shell/zi/issues/564)
- [Zi release proposal #559](https://github.com/z-shell/zi/issues/559)
- [ADR-0007](0007-release-publication-flow.md)
- [ADR-0019](0019-trunk-on-main-default.md)
- [GitHub Actions events triggered by `GITHUB_TOKEN`](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [GitHub repository rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets)
