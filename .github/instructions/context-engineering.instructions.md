---
description: "Guidelines for structuring repository context and prompting to maximize AI assistant efficiency across Z-Shell repositories"
applyTo: "**"
---

# Context Engineering Guidelines

Best practices for providing concise, high-signal context to AI models working within Z-Shell repositories.

---

## 1. Context Principles

- **Progressive Discovery**: Rely on root `AGENTS.md` for organization policy and load scoped `.github/instructions/*.instructions.md` only when modifying matched file patterns.
- **Locality of Reference**: Focus context on the target repository and immediate dependencies. Avoid pulling unrelated child repository state into the active context.
- **Symbol & Path Precision**: Reference exact file paths (e.g., `functions/z-a-patch`, `tests/zunit/test-load.zunit`) and exact function names to avoid ambiguity.

---

## 2. Shell & Multi-Repo Context

- **Declare Dialect Explicitly**: Specify whether the task targets native Zsh (for `zi` / annexes / plugins), POSIX `sh` (for bootstrap scripts), or Go (for `zsh-lint`).
- **Provide Compatibility Floor**: When asking for syntax changes or refactoring, state the repository compatibility floor (e.g., Zsh 5.1+ or Zsh 5.8+).
- **Separate Planning from Execution**: For multi-file changes or cross-repo modifications, align on a scoped plan before performing mutations.
