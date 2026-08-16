---
description: "Canonical procedure for the generator-verifier dual-phase review pattern: when to escalate a draft to adversarial verification and how to run that verification"
applyTo: "**"
---

# Generator-Verifier Workflow

A structured procedure for producing high-reliability designs, complex parser
logic, security-relevant workflows, and AST algorithms by decoupling initial
rapid synthesis from adversarial verification. This document owns the
**escalation and phase structure**. It does not restate review dimensions —
for what to check during verification, use the canonical
[Code Review Guidelines](./code-review-generic.instructions.md).

---

## Phase 1: Draft Generation

Produce an initial end-to-end working draft or architectural design without
premature optimization.

1. **State assumptions**: explicitly list core operational assumptions,
   constraints, and dependencies.
2. **Draft the solution**: write the complete architectural blueprint or code
   implementation.
3. **Identify fragile areas**: tag sections with high uncertainty, performance
   bottlenecks, or boundary edge cases.

---

## Phase 2: Escalation Gate

Evaluate whether the task requires deep dual-phase verification or can be
finalized immediately.

### Escalation triggers (activate verification)

- **Concurrency and state**: distributed state, mutexes, locking, race
  conditions, async queues, idempotency.
- **Security and data integrity**: authentication, authorization,
  cryptography, input sanitization, transaction boundaries, data loss risks.
- **System architecture**: multi-component interactions, failover strategies,
  backpressure handling, partitioning.
- **Parser and AST logic**: complex grammar parsing, state machines, AST
  walker mutations, AST grafting, token decoding.
- **Intricate algorithms**: complex math, recursion, custom parsing.

### Negative triggers (direct finalization)

- Standard boilerplate, repetitive CRUD without complex business rules.
- Static styling or routine documentation edits.
- Simple, deterministic single-purpose utility functions.
- Routine repository maintenance (e.g., branch cleanup, issue labeling).

Security- and review-flavored work that does not otherwise escalate here still
falls under the always-applicable
[Code Review Guidelines](./code-review-generic.instructions.md); this gate
decides only whether the *heavier* generator-verifier loop below also applies.

---

## Phase 3: Deterministic Tooling

Before LLM-based advisory critique, run deterministic tools where applicable:

- Syntax checks, type checkers, and linters (e.g., `go vet ./...`,
  `zsh -f -n`, `git diff --check`).
- Relevant unit or regression test suites (e.g., `go test ./...`, `zunit`).

Formulate the review rubric from the canonical
[Code Review Guidelines](./code-review-generic.instructions.md) priority
hierarchy (CRITICAL / IMPORTANT / SUGGESTION), scoped to the draft's fragile
areas from Phase 1. Do not maintain a second, parallel rubric here.

---

## Phase 4: Verification Review Execution

- **Standard tasks (self-review)**: step into an adversarial reviewer
  persona. Evaluate the draft against the scoped rubric and record specific
  failure modes or counter-examples.
- **High-stakes tasks (subagent isolation)**: spawn an isolated research or
  self subagent. Provide the draft and the rubric to evaluate the
  implementation independently without context bias.

---

## Phase 5: Synthesis and Correction

1. **Apply corrections**: address valid critique items directly in the
   implementation.
2. **Verify convergence**: limit revision loops to a maximum of 2 iterations
   to avoid circular over-refinement.
3. **Deliver the final artifact**: present the refined solution along with a
   concise summary of verified properties and any residual architectural
   trade-offs.
