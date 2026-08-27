---
description: "Portable worktree discovery, placement, ownership, and cleanup boundaries"
applyTo: "**"
---

# Worktree Management Instructions

Use `git worktree list --porcelain` from the owning repository as the source of
truth. A directory scan, runtime sidebar, or remembered path is not a complete
inventory.

Before creating a worktree:

1. Read `runbooks/worktrees.md` and the owning repository's branch guidance.
2. Use the repository-provided worktree helper when one exists.
3. Use the stable worktree root declared by that repository or workspace.
4. Start detached unless the approved task requires a branch and its exact name
   has been selected under the repository's branch model.

Do not create a worktree in `/tmp`, an arbitrary sibling directory, or an
untracked location chosen only by one runtime. Do not use a linked worktree of
a Git superproject for work that needs initialized submodules. Create worktrees
from the owning child repositories, or use an independent clone when the whole
superproject must be isolated.

Listing and checking worktrees must remain read-only. Moving, removing,
pruning, repairing, or deleting a worktree or its registration requires
separate authorization after its branch, dirty state, and recoverability have
been verified.
