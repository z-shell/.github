# 11. zsh-lint Semantic Analyzer Architecture

Date: 2026-05-29

## Status

PROPOSED

## Context

`zsh-lint` is a standalone Go semantic analyzer for Zsh. Its parser front end
produces an `mvdan/sh/syntax` tree, and its semantic engine must support rules
that need only the current syntax node as well as rules that need declarations
collected from the complete file.

Zsh permits dynamic behavior and declarations whose textual order does not
necessarily match the facts an analysis needs. A complete-file declaration
index can therefore be useful, but requiring one for every rule would couple
syntax-only checks to state they do not consume. The index is an intentionally
approximate symbol map, not flow-sensitive local/global resolution.

Rule behavior and diagnostic compatibility also depend on contracts outside
the traversal strategy. Stable rule IDs and evidence requirements, parser-gap
handling, inline suppression, and machine-readable output are governed by the
linked `zsh-lint` contracts rather than duplicated here.

## Decision

Use a **conditional two-pass semantic core inside a three-phase diagnostic
pipeline**:

1. **Optional scope indexing.** Before rule evaluation, build the declaration
   index only when at least one registered rule implements `ScopeAwareRule` and
   returns `NeedsScope() == true`. The index records the declarations and
   approximate function-local/global associations exposed by `scope.Map`.
2. **Rule evaluation.** Walk the syntax tree and pass each node, with a shared
   `*Context`, to every registered rule. `Context` carries the parsed file,
   source path, diagnostics, and a declaration index populated only when
   requested. Its `Report` method accepts source positions, a stable rule ID,
   severity, and message.
3. **Suppression and finalization.** Collect and apply inline suppression
   directives, preserve or add `meta/*` diagnostics required by the suppression
   contract, and sort the resulting diagnostics once in deterministic order.

The analyzer's extension interfaces are:

```go
type Rule interface {
    ID() diag.RuleID
    Name() string
    Analyze(ctx *Context, node syntax.Node)
}

type ScopeAwareRule interface {
    NeedsScope() bool
}
```

`ScopeAwareRule` is an opt-in capability, not a requirement for all rules.
Scope-dependent rules may query the declaration index, but they must account
for its approximate, non-flow-sensitive model when defining their semantics.

The semantic pipeline produces the common diagnostic model. Suppression
semantics and the versioned JSON envelope remain product contracts in the
owning repository; changing either contract requires following its documented
compatibility rules rather than changing this ADR alone.

## Consequences

### Positive

- Syntax-only rules do not pay the indexing cost or depend on scope state.
- Rules that need complete-file declaration facts can opt into a shared index
  without embedding traversal-order mutation in each rule.
- A common reporting and finalization path keeps rule diagnostics, suppression,
  metadata diagnostics, and deterministic output aligned.
- The scope implementation can evolve behind the existing `scope.Map` boundary
  while preserving its rule-facing API and applicable diagnostic contracts.

### Costs and limits

- Enabling scope indexing adds a tree traversal; the cost depends on the
  enabled rule capabilities and input, and this ADR makes no unmeasured
  performance guarantee.
- The declaration index cannot by itself justify flow-sensitive or high-accuracy
  claims. A rule that needs stronger resolution must first define and test that
  capability in the owning repository.
- Shipping a rule requires more than satisfying the Go interface: it also needs
  a stable ID, registry entry, tests, generated reference documentation, and the
  evidence required by the rule policy.
- Suppression and finalization form a separate phase that the analyzer must keep
  consistent across human- and machine-readable output.

## Alternatives considered

1. **Unconditional two-pass analysis.** Always build the declaration index
   before evaluating rules. Rejected because it makes syntax-only rules depend
   on and pay for state they do not consume.
2. **Single-pass state mutation as the only engine model.** Build context while
   evaluating rules in one traversal. Rejected as the sole model because
   analyses that require complete-file facts would become dependent on textual
   traversal order. Rules that need only local syntax still operate entirely in
   the evaluation phase.
3. **Flow-sensitive symbol analysis.** Build control-flow and data-flow models
   for precise runtime ordering and scope. Not adopted by this decision, which
   specifies an approximate declaration index. A rule that genuinely requires
   stronger semantics should motivate a separate design change with Zsh-manual
   grounding and corpus evidence.
4. **Regex-based linting over raw source.** Use regular expressions instead of a
   syntax tree. Rejected as the semantic engine because raw text does not retain
   shell grammar context and cannot reliably distinguish code from strings or
   comments.

## Decision review

This reconciliation remains a proposal. Maintainers should explicitly accept
it with a named decider and date, amend it, supersede it with another ADR, or
reject it. Until that decision is recorded, this document describes the
implemented architecture but does not claim maintainer acceptance.

## References

- [Issue #455 — Reconcile proposed zsh-lint architecture ADR 0011](https://github.com/z-shell/.github/issues/455)
- [`zsh-lint` analyzer orchestration](https://github.com/z-shell/zsh-lint/blob/main/internal/analyzer/analyzer.go)
- [`Rule` and `ScopeAwareRule` interfaces](https://github.com/z-shell/zsh-lint/blob/main/internal/analyzer/rule.go)
- [`Context` reporting API](https://github.com/z-shell/zsh-lint/blob/main/internal/analyzer/context.go)
- [`scope.Map` declaration model](https://github.com/z-shell/zsh-lint/blob/main/internal/scope/scope.go)
- [`zsh-lint` rule policy](https://github.com/z-shell/zsh-lint/blob/main/docs/project/rule-policy.md)
- [`zsh-lint` inline suppression contract](https://github.com/z-shell/zsh-lint/blob/main/docs/project/suppression.md)
- [`zsh-lint` machine-readable output contract](https://github.com/z-shell/zsh-lint/blob/main/docs/project/output-contract.md)
- [`zsh-lint` parser-gap workflow](https://github.com/z-shell/zsh-lint/blob/main/docs/project/parser-gap-workflow.md)
- [Zsh manual](https://zsh.sourceforge.io/Doc/Release/)
