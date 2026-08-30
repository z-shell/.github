# 18. Adopt Portable Worktree Management

- **Status:** ACCEPTED
- **Date:** 2026-08-27
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

Agent runtimes can create Git worktrees in different locations and maintain
their own managed-worktree views. A runtime can therefore report zero
worktrees while the owning repositories still register several linked
worktrees elsewhere. Directory scans are also insufficient: they miss external
paths, cannot identify stale registrations reliably, and can mistake ordinary
directories for worktrees.

Temporary placement creates a second failure mode. A directory under `/tmp`
can disappear while its registration and branch ownership remain in the Git
repository. The stale record can then constrain later branch operations even
though no agent can find the original checkout.

Multi-repository workspaces add an ownership problem. A superproject and each
submodule have separate worktree registries. Git documents incomplete submodule
support for multiple superproject checkouts and recommends against relying on
that combination. A portable standard must therefore identify the owning
repository before it chooses a path or invokes Git.

## Decision

Adopt these organization-wide worktree rules:

1. The owning repository's output from `git worktree list --porcelain` is the
   authoritative inventory. Runtime UIs, directory scans, and local memory are
   partial views only.
2. Each repository or multi-repository workspace declares one stable root for
   new manual worktrees. Paths identify the owning repository and task. New
   worktrees do not use `/tmp` or an ad hoc sibling directory.
3. Runtime-managed and manual worktrees use separate lifecycle subtrees when
   they share a physical root. Runtime retention and cleanup apply only to the
   runtime-managed subtree.
4. Worktrees are created from the repository that owns the change. In a
   submodule workspace, child repositories are the normal worktree unit.
5. A linked superproject checkout is not used for work that needs initialized
   submodules. A fully isolated superproject uses an independent clone.
6. Shared inventory tooling queries Git for the workspace repository and every
   initialized child. It does not maintain a second mutable registry.
7. Inventory and health checks are read-only. Moving, removing, pruning,
   repairing, or deleting a worktree or registration requires separate
   authorization after recoverability is verified.
8. Mandatory behavior is delivered through `AGENTS.md` and routed instruction
   surfaces. Optional runtime hooks, skills, or sidebars cannot own the rule.

`runbooks/worktrees.md` owns the operational procedure.

## Consequences

### Positive

- Every supported runtime can discover the same set of registered worktrees.
- New worktrees have predictable, durable paths and clear repository ownership.
- Runtime-managed cleanup cannot silently become the cleanup policy for manual
  worktrees.
- Stale or temporary registrations become visible without mutating them.
- Child-repository work avoids the unsupported superproject and submodule
  combination.

### Negative

- Multi-repository inventories require one Git query per initialized child.
- Existing noncanonical worktrees remain visible until separately reviewed and
  retired.
- Runtime sidebars remain partial views, so maintainers need the shared
  inventory command for cross-runtime coordination.
- Fully isolated cross-repository work requires a separate clone and more disk
  space.

## Alternatives considered

### Use one runtime's managed directory as the only source of truth

Rejected because other runtimes and command-line Git do not share its lifecycle
metadata, and manually created worktrees may not appear in its UI.

### Discover worktrees by scanning a common directory

Rejected because valid worktrees can remain outside the directory, stale Git
registrations have no live directory, and ordinary directories can resemble
worktrees.

### Put all worktrees under `/tmp`

Rejected because temporary cleanup can remove the checkout without removing
its Git registration or releasing its branch.

### Create one linked superproject worktree per task

Rejected as the default because Git documents incomplete support when
superproject worktrees contain initialized submodules.

## References

- [z-shell/.github#542](https://github.com/z-shell/.github/issues/542)
- `runbooks/worktrees.md`
- `runbooks/instruction-update.md`
- `decisions/0014-portable-agent-instruction-architecture.md`
- [Git worktree documentation](https://git-scm.com/docs/git-worktree.html)
