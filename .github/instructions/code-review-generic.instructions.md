---
description: "Canonical code review standards for Z-Shell repositories covering shell dialects, plugin standards, security, and verification"
applyTo: "**"
excludeAgent: "cloud-agent"
---

# Code Review Guidelines

Structured review standards for inspecting pull requests, patches, and code changes across Z-Shell repositories.

---

## 1. Review Priorities

Evaluate findings according to the following hierarchy:

### 🔴 CRITICAL (Blocks merge)

- **Security**: Untrusted input execution, unreviewed `eval`, exposed tokens/secrets, unsafe temporary file creation.
- **State Integrity**: Uncontrolled global shell state contamination, failure to honor a declared unload contract, irreversible side effects.
- **Dialect Violations**: Bash-only syntax in native Zsh files, or non-POSIX constructs in `/bin/sh` scripts.
- **Breaking Changes**: Undocumented modifications to plugin loading interfaces, CLI arguments, or configuration schemas.

### 🟡 IMPORTANT (Requires resolution before merge)

- **Compatibility Floor**: Using language features above the repository's declared minimum Zsh/tool version floor without fallback.
- **Execution Profiles**: Misclassifying source execution profiles (`sourced-library` vs `autoload-function` vs `startup-file`).
- **Test Coverage**: Lack of regression or unit tests (`.zunit` or Go test fixtures) for new features or bug fixes.
- **CI / Workflow Compliance**: Violations of action SHA pinning or permissions baselines.

### 🟢 SUGGESTION (Non-blocking improvements)

- **Idiomatic Optimization**: Leveraging native parameter expansions over subshells (`$(...)`) where performance matters.
- **Readability & Style**: Minor naming inconsistencies, comment clarity, or file structure formatting.

---

## 2. Review Methodology

1. **Classify Dialect & Profile**:
   - Confirm whether the code is native Zsh, Bash, POSIX `sh`, or Go before applying rules.
   - For Zsh, follow `.github/instructions/zsh-scripting.instructions.md` and `lib/zsh-standard-policy.json`.
2. **Execute Deterministic Checks First**:
   - For Zsh syntax: run `zsh -f -n <file>` to verify native validity.
   - For POSIX `sh`: run `sh -n <file>`.
   - Run relevant test suites (`zunit`, `go test`, `npm test`) when available.
3. **Inspect Lifecycle & Cleanup**:
   - Verify that any global state (`fpath`, environment variables, aliases, functions) is cleanly scoped or reversible upon plugin unload.
4. **Enforce Passive Loading**:
   - Verify that plugin sourcing paths perform no implicit network calls or heavy blocking operations.

---

## 3. Finding Format

Structure code review feedback with concrete evidence and actionable fixes:

````markdown
- **Severity**: [CRITICAL | IMPORTANT | SUGGESTION]
- **Rule / Category**: [e.g., zsh/plugin/exact-lifecycle or security/untrusted-eval]
- **Location**: `path/to/file:line`
- **Impact**: Explanation of the concrete failure mode or risk.
- **Correction**:
  ```zsh
  # Proposed fix
  ```
````

```

```
