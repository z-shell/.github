# 14. Adopt portable agent-instruction delivery

- **Status:** ACCEPTED
- **Date:** 2026-07-23
- **Deciders:** ss-o
- **Supersedes:** `decisions/0001-meta-repo-and-agents-md.md` vendor-entry-point layout
- **Superseded by:** None

## Context

ADR 0001 established `AGENTS.md` as the shared entry point for organization
instructions, but its vendor-entry-point layout assumed that additional root
files could safely redirect runtimes to that baseline. That assumption does not
hold consistently across standalone clones, runtimes, or operating systems.
Symlinks are especially fragile, and pointer-only private instructions can hide
mandatory public policy from runtimes that do not follow the pointer.

The organization now has public and private instruction surfaces with different
privacy boundaries. Maintainers need one portable ownership and delivery model
that keeps public policy standalone, permits a private overlay without copying
policy by hand, and makes every material instruction change reviewable across
all supported runtimes and repository contexts.

The maintainer accepted this ADR on 2026-07-23. ADR 0001 remains the historical
basis for the organization meta-repository, while this decision supersedes its
vendor-entry-point layout.

ADR number 0013 is reserved by the separate repository-settings proposal and is
not modified here.

## Decision

Adopt the following instruction architecture:

1. The public `AGENTS.md` is the canonical organization baseline. It is a
   standalone instruction document and does not require another repository,
   hook, agent, or skill to be understood.
2. Organization repository roots do not contain `CLAUDE.md` or `GEMINI.md`.
   Runtimes consume `AGENTS.md` directly or use a supported repository-local
   adapter outside the root when runtime mechanics require one.
3. The private maintainer workspace may use root-level `CLAUDE.md` and
   `GEMINI.md` vendor adapters as the sole exception to the root-file rule.
4. Private delivery is generated as one composite containing the public
   baseline followed by a private overlay. The generated composite is the
   delivered instruction surface; maintainers do not maintain a pointer-only
   private instruction file.
5. JSON manifests classify every active instruction surface by ownership,
   authority, consumers, task routing, path, and review responsibility. The
   public and private manifests are the inventories used to detect missing,
   duplicate, or contradictory routes.
6. Runtime adapters are regular import-only files. They contain only the
   runtime-specific import needed to reach the delivered instructions and are
   not symlinks or secondary policy owners.
7. Mandatory policy cannot depend only on optional hooks, agents, or skills.
   Those mechanisms may improve discovery or execution, but every supported
   runtime must receive mandatory rules through its baseline or generated
   composite.
8. Public and private validators enforce drift, declared paths, adapter shape,
   privacy boundaries, and the 32,768-byte instruction-size cap. A change is
   incomplete until all validators applicable to its owning repository pass.
9. Runtime discovery checks remain manual because runtime behavior cannot be
   proved by repository validation alone. A pull request may report a manual
   check as unverified when the runtime is unavailable, but it must not imply
   that the check passed.

Every material instruction change follows the impact-review workflow in
`runbooks/instruction-update.md` so ownership, routing, generated output, and
runtime delivery are evaluated together.

## Consequences

### Positive

- Public organization policy remains usable from a standalone clone.
- Private policy composes with the public baseline without duplicating it by
  hand or exposing private context publicly.
- Manifests make instruction ownership and runtime routing explicit and
  machine-checkable.
- Regular import-only adapters behave consistently across platforms and cannot
  silently become competing policy sources.
- The required impact review catches cross-surface drift before a material
  instruction change is merged.
- Automated validators and explicit manual-check status separate what the
  repository proves from what still requires runtime observation.

### Negative

- Maintainers must update manifests and answer an impact review for material
  instruction changes.
- Generated private composites add a synchronization step and must be checked
  for drift.
- Supporting several runtime discovery mechanisms still requires manual checks.
- The size cap may require concise canonical prose or better routing as policy
  grows.

## Alternatives considered

1. **Pointer-only private instructions:** Rejected because a runtime that does
   not resolve the pointer can miss mandatory public policy, and the private
   overlay is not delivered as one auditable artifact.
2. **Vendor-specific imports without a composite:** Rejected because each
   runtime would assemble public and private sources differently, leaving
   ordering and completeness outside validator control.
3. **Per-repository vendor files:** Rejected because root `CLAUDE.md` and
   `GEMINI.md` files would multiply policy surfaces and create organization-wide
   drift.
4. **Symlink-only adapters:** Rejected because symlink handling varies across
   tools, platforms, and checkouts, and a symlink does not provide a portable
   runtime import contract.

## References

- [z-shell/.github#475](https://github.com/z-shell/.github/issues/475)
- `AGENTS.md`
- `runbooks/instruction-update.md`
- `.github/instruction-surfaces.json`
- ADR-0001: `decisions/0001-meta-repo-and-agents-md.md`
