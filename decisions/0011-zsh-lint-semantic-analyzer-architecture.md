# 11. zsh-lint Semantic Analyzer Architecture

Date: 2026-05-29

## Status

PROPOSED

## Context

`zsh-lint` is transitioning from a legacy interactive shell plugin to a standalone, Go-based semantic analyzer (Epic ZSH-3). The parser front end relies on `mvdan/sh/syntax`. We need a unified architecture for how the tool will traverse the Abstract Syntax Tree (AST), manage contextual state (like variable scoping), and evaluate linting rules. 

Shell scripts are highly dynamic, meaning a single-pass naive visitor pattern is often insufficient to detect complex issues (e.g., using a variable before it is declared, or aliasing).

## Decision

We will implement a **Two-Pass Analysis Architecture** for the semantic engine:

1. **Pass 1: Context & Scope Resolution (The Indexer)**
   - Traverses the `syntax.File` AST to build a `ScopeMap`.
   - Records variable declarations, function definitions, and alias definitions.
   - Determines the boundaries of local vs. global scope.
2. **Pass 2: Rule Evaluation (The Linter)**
   - Traverses the AST a second time.
   - Feeds each `syntax.Node` to a registry of initialized `Rule` implementations.
   - Passes a rich `*AnalyzerContext` object alongside the node, which provides the rules access to the `ScopeMap` generated in Pass 1, as well as a `Report(diagnostic)` method.

### The Rule Interface
To ensure extensibility, every rule must satisfy a strict interface:
```go
type Rule interface {
    Name() string
    Analyze(ctx *AnalyzerContext, node syntax.Node)
}
```

## Consequences

### Positive
- **Decoupled Rules**: Rule authors do not need to worry about scope resolution; they can simply query `ctx.IsDeclared("varName")`.
- **Extensibility**: Adding a new lint rule requires only writing a struct that satisfies the `Rule` interface and registering it in the engine.
- **Precision**: Two passes allow the engine to detect "use before declaration" errors with high accuracy.

### Negative
- **Performance Overhead**: Walking the AST twice per file is slower than a single pass. However, `mvdan/sh` is highly optimized in Go, so the impact on typical shell scripts should be negligible compared to the architectural clarity gained.
- **Complexity**: Managing the `AnalyzerContext` state between passes introduces slight complexity to the core engine.

## Alternatives Considered

1. **Single-Pass State Mutation**: A single traversal that builds scope and evaluates rules simultaneously. 
   - *Rejected* because shell functions can be declared at the bottom of a file but invoked at the top. A single pass would yield false positives for "undefined function" errors.
2. **Regex-Based Linting**: Using `regexp` against the raw file string.
   - *Rejected* because it completely ignores the structural context of the shell grammar, leading to massive false-positive rates (e.g., matching a keyword inside a string literal).