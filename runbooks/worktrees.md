# Runbook: Worktree Management

Use this runbook to create, discover, hand off, and retire Git worktrees across
agent runtimes. Repository-specific helpers and paths may narrow these rules,
but they must preserve the discovery and safety boundaries below.

## Sources of truth

The owning Git repository's worktree registry is authoritative. Enumerate it
with:

```bash
git -C <repository> worktree list --porcelain
```

In a multi-repository workspace, run the command for the workspace repository
and every initialized child repository. A runtime UI normally reports only the
worktrees that runtime created or manages. A filesystem scan misses external
paths and cannot reliably distinguish live worktrees from stale directories.

Use the repository-provided inventory helper when one exists. It should query
Git rather than maintain a second mutable registry.

## Placement

Each repository or workspace declares one stable worktree root. New manual
worktrees belong beneath that root and use a path that identifies the owning
repository and task. Reserve a separate subtree for runtime-managed worktrees
when a runtime performs its own lifecycle management.

Do not create new worktrees in `/tmp` or in an arbitrary sibling directory.
Temporary directories can disappear while their Git registrations and branch
ownership remain. Do not move a live noncanonical worktree merely to satisfy
the placement rule; report it and migrate it only through an approved cleanup.

## Repository ownership

Create a worktree by invoking Git from the repository that owns the change.
Select the starting point from that repository's current branch model instead
of assuming one organization-wide default branch.

Git documents incomplete submodule support for multiple checkouts of a
superproject. Do not use a linked superproject checkout for work that needs
initialized submodules. Prefer worktrees of the affected child repositories.
Use an independent clone when a fully isolated superproject and its submodules
must move together.

## Creation

Before creation:

1. List every existing worktree for the owning repository.
2. Confirm the requested task is not already active elsewhere.
3. Resolve and verify the exact starting ref.
4. Confirm the target is contained by the declared worktree root.
5. Confirm the target path does not already exist and is not a symlink or
   special file.

Prefer a detached worktree for exploratory or concurrent agent work. Create a
branch only when implementation authority includes that branch and its name is
valid under the owning repository's branch model. Git permits a branch to be
checked out in only one worktree at a time.

## Handoff

A handoff records:

- owning repository;
- absolute or workspace-relative worktree path;
- current HEAD and branch, or detached state;
- dirty state;
- starting ref and task or issue;
- validation already run;
- whether the worktree is runtime-managed, manual, locked, or prunable.

Never rely only on a runtime sidebar or local memory to communicate the
worktree's existence.

## Inspection and cleanup

Inventory and health commands are read-only. They may report temporary,
external, noncanonical, locked, or prunable registrations, but they do not fix
them automatically.

Before moving, removing, pruning, repairing, or deleting anything:

1. Resolve the exact owning repository and registered path.
2. Check branch, HEAD, upstream, dirty files, and untracked files.
3. Confirm whether commits have landed or remain recoverable elsewhere.
4. Obtain explicit authorization for the exact cleanup action.
5. Use `git worktree` operations rather than deleting a directory directly.
6. Re-list the registry and verify the intended registration changed.

## Runtime-specific management

Runtime-managed worktrees may use separate metadata, retention, snapshots, or
handoff behavior. Keep their lifecycle subtree separate from manual worktrees,
and do not manipulate it with a generic cleanup command. The owning Git
registry remains the common inventory that every runtime can query.

## See also

- `decisions/0018-portable-worktree-management.md`
- `decisions/0008-branching-model.md`
- `runbooks/instruction-update.md`
