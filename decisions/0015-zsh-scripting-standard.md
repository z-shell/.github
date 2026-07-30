# 15. Adopt an organization-wide Zsh scripting standard

- **Status:** PROPOSED
- **Date:** 2026-07-29
- **Deciders:** Pending maintainer acceptance
- **Supersedes:** None
- **Superseded by:** None

## Context

Z-Shell repositories contain executable scripts, sourced libraries, autoloaded
functions, and test fixtures with different lifecycle and compatibility needs.
Without one organization-wide standard, repositories can infer conflicting
minimum versions, accept third-party parser results over native Zsh behavior,
or duplicate policy in hand-maintained files.

The organization needs one public policy hierarchy that names semantic authority,
defines durable rule identifiers and source classes, and can be delivered to
repositories without making generated copies independent policy owners.

## Decision

The released official Zsh manual is the semantic authority. Zsh 5.9.2, released
2026-07-12, is recorded as the reviewed stable release. Development material is
non-normative.

Compatibility combines a per-repository compatibility floor with validation on
the current stable release. No global fallback floor is inferred.

The standard distinguishes five source classes: `standalone-executable`,
`startup-file`, `sourced-library`, `autoload-function`, and `test-fixture`.
These startup and shutdown files are read by Zsh for defined lifecycle phases
and may make phase-owned effects, unlike caller-preserving sourced libraries.

Detailed normative prose lives in
`.github/instructions/zsh-scripting.instructions.md`. Machine-readable release,
rule, profile, and source-class data lives in `lib/zsh-standard-policy.json`.

Enrolled repositories eventually receive generated, digest-checked delivery in
repository-local artifacts. Generated artifacts are consumers, not policy owners.

Source classification uses one machine contract and fails on ambiguous evidence.
The classifier implementation is deferred to Phase 2.

Enforcement is layered: editor hygiene, native syntax and compilation,
supplemental semantic lint, runtime/lifecycle tests, and review.

ShellCheck is not used for Zsh. Third-party parser rejection cannot override
native Zsh validity.

Enrollment requires separate repository-scope approval, an evidence-backed
minimum version, explicit overrides or waivers, and repository-owned tests.
Initial policy delivery does not enroll another repository. Every repository
enrollment remains a separately approved and verified change.

## Consequences

Gains include one authority hierarchy, stable rule IDs, consistent task/path
delivery, machine-checkable drift, and explicit compatibility. This gives
maintainers a common basis for review while keeping repository-specific
compatibility evidence visible.

Costs include metadata maintenance, generated delivery, version-lane CI expense,
parser-gap handling, and per-repository enrollment work. The organization must
maintain the policy data and delivery checks, and each repository still needs a
separate, evidence-backed enrollment decision.

## Alternatives considered

1. **Expand the existing Bash-oriented generic shell instruction.** Rejected
   because it cannot express Zsh semantic authority, source classes, and
   compatibility contracts without conflating distinct languages.
2. **Add only a prose style guide.** Rejected because prose alone cannot provide
   stable rule identifiers, machine-checkable drift, or release and profile data.
3. **Make Zsh 5.9.2 a universal minimum.** Rejected because repositories need
   an explicit per-repository compatibility floor instead of an inferred global
   fallback.
4. **Rely on organization-level Copilot inheritance.** Rejected because it does
   not provide portable delivery to every supported runtime or repository.
5. **Rely on ShellCheck or `shfmt`.** Rejected because neither tool defines Zsh
   validity, and third-party parser behavior cannot override native Zsh.
6. **Make `zsh-lint` semantic authority.** Rejected because the released
   official manual, not an implementation, is the semantic authority.
7. **Hand-maintain copies in every repository.** Rejected because independent
   copies drift and would create competing policy owners.

## References

- [Issue #493](https://github.com/z-shell/.github/issues/493)
- [Official Zsh 5.9.2 manual](https://zsh.sourceforge.io/Doc/Release/index.html)
- [Official Zsh release notes](https://zsh.sourceforge.io/releases.html)
- [Official Startup/Shutdown Files reference](https://zsh.sourceforge.io/Doc/Release/Files.html)
- `decisions/0014-portable-agent-instruction-architecture.md`
- `runbooks/instruction-update.md`
