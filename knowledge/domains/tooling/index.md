# Tooling

Select this domain for analyzers, parsers, linters and their supported language boundaries. Implementation detail belongs to the tool's source and instructions.

| Task | Authoritative context |
| --- | --- |
| Understand zsh-lint architecture | [Analyzer decision](../../../decisions/0011-zsh-lint-semantic-analyzer-architecture.md) and [parser strategy](../../../decisions/0023-zsh-lint-parser-front-end-strategy.md) |
| Work on parser internals | [zsh-lint repository](https://github.com/z-shell/zsh-lint), its AGENTS.md, parser-front-end instructions and parser-gap-fix skill |
| Understand parser fork disposition | [ADR-0030](../../../decisions/0030-zsh-lint-parser-fork-trigger-fired.md) |
| Change the CI integration | [zsh-lint CI runbook](../ci/zsh-lint-ci.md) |

## Pending project-source adoption

The [Go AST draft](zsh-lint-go-ast.md) and [parser-front-end draft](zsh-lint-parser-front-end.md) prepare complete version-compatible project instructions. They preserve native frontmatter and refer to project revision `7ff05091a5489becf32069db1738d38ec23c8fd5`. The project instructions, parser-gap-fix skill and source-coupled contracts remain authoritative until approved organization sources are published and project delivery, compatibility and discovery are verified. No project delivery record or source pin is active for these drafts.

Use [Zsh](../zsh/index.md) when deciding whether syntax or behavior is valid Zsh. Supplemental-tool acceptance is not language authority. Do not copy code-derived parser facts into this index.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.
