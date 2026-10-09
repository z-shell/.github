# 39. Zi Main Integration and Signed Milestones

- **Status:** ACCEPTED
- **Date:** 2026-10-08
- **Deciders:** ss-o
- **Supersedes:** The Zi integration exception in `decisions/0019-trunk-on-main-default.md` and `decisions/0028-zi-promotion-is-release-authorization.md`, after verified cutover
- **Superseded by:** None

## Context

Zi is consumed directly from `main`. Its full focused Zsh matrix already runs on ordinary `next` pull requests; promotion adds ZD compatibility, full Trunk and CodeQL checks, clean startup and real-object lifecycle checks. Those checks protect users, but a second persistent integration branch is not necessary to run them. Batch promotion also couples otherwise ready changes and requires separate issue-closure and release-identity machinery.

The coordinated migration is tracked in [#771](https://github.com/z-shell/.github/issues/771), with organization policy in [#772](https://github.com/z-shell/.github/issues/772) and Zi implementation in [zi#628](https://github.com/z-shell/zi/issues/628).

## Decision

After maintainer acceptance on `main` and the verified cutover below, Zi follows the organization's protected `main` integration model. Until then, ADR-0019 and ADR-0028 remain operative.

1. Ordinary topic branches start from current `main` and target `main`. Every merge can reach Git consumers immediately. Keep incomplete behavior on its topic branch and require applicable review of record, signatures, resolved review threads and successful qualification before merge.
2. Every ordinary `main` pull request runs the full Linux/macOS matrix on Zsh 5.8.1, 5.9 and 5.9.2, ZD native and compatibility validation, full Trunk checks, CodeQL, clean installation/startup and real-object install/update/unload/delete checks. The required aggregate gate fails when any constituent fails, is cancelled or is skipped. Candidate-head evidence must be revalidated against a changed base; the resulting merge remains subject to post-merge checks.
3. Preserve the existing installation and self-update channels on `main`. Switching users to stable tags is a separate product change.
4. Merging an ordinary pull request does not authorize a semantic tag or GitHub release. A maintainer separately reviews the deterministic release plan for a full SHA on current protected `main`, including its semantic version and notes, then pushes a signed annotated tag identifying that exact SHA. The existing tag-driven verifier and publisher become the normal milestone path. Do not add a proposal issue or a release on every merge.
5. Before publication, verify the tag's signature and authorized signer, exact target and complete required-workflow allowlist on that SHA. Reject incomplete, failed or stale evidence. Preserve existing-tag conflict detection, idempotent publication and protected immutable tag rules. A no-op release plan produces no tag or release.
6. Retain historical tags, promotion merge ancestry and decision records. Native issue-closing keywords on ordinary default-branch PRs replace promotion-only issue closure after historical issues are reconciled.

## Cutover and rollback

1. Inventory both branches' commits and trees, tags, open PRs, required checks, rulesets, bots, installer/wiki references, workspace task bases and downstream tracking declarations. Preserve every retained change and its owner.
2. Land the replacement qualification and release paths under the current branching rules. Keep promotion-only publication disabled before admitting ordinary `main` PRs.
3. Observe the new required contexts on a real `main` PR, including fork-safe execution. Confirm a failed, skipped or cancelled constituent cannot produce a passing aggregate. Preserve source-guard enforcement until replacement rules are ready; stage any guard removal without a ruleset bypass.
4. Switch the protected `main` required contexts and source policy together, then switch contribution guidance and dependency automation. Keep signed commits, applicable review controls and force-push/deletion protections. Do not require linear history to rewrite existing promotion ancestry.
5. Verify fresh installation, existing-clone self-update and failure recovery on the delivered `main` SHA. Reconcile historical issue closure, retained commits and open PRs before separately authorized retirement of remote `next` and its obsolete ruleset.
6. If qualification or enforcement fails before cutover, retain the existing model. After cutover, repair or revert through reviewed topic PRs into protected `main`; do not reset or force-push stable history. A rollback to persistent `next` needs restored qualification, rules and contribution guidance, with branch recreation separately authorized.

## Consequences

Ready fixes reach stable consumers independently and ordinary contributions use GitHub's default-branch issue closure. Qualification moves earlier instead of disappearing. Each merge has direct user exposure, making small changes, base revalidation and rollback discipline essential. Milestone publication has one separate human authorization through an existing signed-tag path; it does not require a new release system or signing key in Actions.

## Cutover evidence: 2026-10-09

- [Zi #629](https://github.com/z-shell/zi/pull/629) staged qualification under the old branch contract. [Promotion #630](https://github.com/z-shell/zi/pull/630) retained the reviewed next tree and both historical parents. [Hotfix #632](https://github.com/z-shell/zi/pull/632) repaired caller/reusable concurrency; [full main-push qualification](https://github.com/z-shell/zi/actions/runs/37962770980) passed on `07743c2399ccce9fb1faeec1c598e149986edb9d` before replacement protection was applied.
- The real fork [cutover PR #631](https://github.com/z-shell/zi/pull/631) passed [all 21 stable-qualification jobs](https://github.com/z-shell/zi/actions/runs/37964278844) on reviewed head `fbd1da4e222ad81b8515abcdcf887a28a27dc846`. All eleven replacement required contexts passed. After its elected [review of record](https://github.com/z-shell/zi/pull/631#pullrequestreview-5474210766), the normal protected squash merge delivered signed main `22b6da908579e6e8143a0abe02e6da14e7b4d5b8`, with the reviewed tree unchanged and prior main as its parent.
- Live main rules were read back with eleven strict checks, signed commits, resolved threads, deletion/force-push protection, merge/squash methods and no bypass actors. Release-tag creation was restricted to the existing administrator role, retaining update/deletion protection and adding no actor or signing key. No milestone tag or release was created.
- Fresh installation/startup and an existing clone's public-main self-update from `07743c23` to `22b6da90` passed in isolated Linux Zsh 5.9.2 state. A failed fetch preserved the checkout and loaded revision; retry succeeded. Hosted macOS qualification is separate evidence.
- [Historical issue reconciliation](https://github.com/z-shell/zi/actions/runs/37948678641) and a read-only replay found no outstanding unqualified closing clause. Retained next has no commits absent from main; remote next and its protection remain until downstream synchronization and separately authorized retirement. Existing topic work and its owners are preserved.

## Alternatives considered

- Keep persistent `next`: valid when owned user-soak feedback adds evidence unavailable before merge, but that value has not been established by the inspected checks alone.
- Publish automatically on every `main` merge: rejected because integration approval does not identify a separately reviewed milestone version and notes.
- Add a new privileged release-dispatch publisher: unnecessary while the existing signed-tag path supplies exact-SHA authorization and validation.
- Move stable consumers to tags: potentially useful for a distinct cadence, but requires separately specified installer/updater migration and rollback behavior.

## References

- [Migration parent #771](https://github.com/z-shell/.github/issues/771)
- `decisions/0019-trunk-on-main-default.md`
- `decisions/0028-zi-promotion-is-release-authorization.md`
- `runbooks/release.md`
- [Zi contribution guidance](https://github.com/z-shell/zi/blob/main/docs/CONTRIBUTING.md)
