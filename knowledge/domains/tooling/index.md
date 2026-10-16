# Tooling

Select this domain for analyzers, parsers, linters and their supported language boundaries. Implementation detail belongs to the tool's source and instructions.

| Task                               | Authoritative context                                                                                                                                                        |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Understand zsh-lint architecture   | [Analyzer decision](../../../decisions/0011-zsh-lint-semantic-analyzer-architecture.md) and [parser strategy](../../../decisions/0023-zsh-lint-parser-front-end-strategy.md) |
| Work on parser internals           | [zsh-lint repository](https://github.com/z-shell/zsh-lint), its AGENTS.md, parser-front-end instructions and parser-gap-fix skill                                            |
| Understand parser fork disposition | [ADR-0030](../../../decisions/0030-zsh-lint-parser-fork-trigger-fired.md)                                                                                                    |
| Change the CI integration          | [zsh-lint CI runbook](../ci/zsh-lint-ci.md)                                                                                                                                  |

## Pending project-source adoption

The [Go AST source](zsh-lint-go-ast.md) and [parser-front-end source](zsh-lint-parser-front-end.md) supply complete version-compatible project instructions. They preserve native frontmatter. The Go AST source refers to project revision `7ff05091a5489becf32069db1738d38ec23c8fd5`, and the parser-front-end source to `f1c43fac9c8eadfc914a4af89a1beea11afca891`. Both have approved records in the [project delivery manifest](../../project-delivery.json), and z-shell/zsh-lint carries their generated consumers, which its Org Routing check verifies. The parser-gap-fix skill and the project's source-coupled contracts stay owned by the project. Native runtime discovery of the generated instructions is not yet verified.

Use [Zsh](../zsh/index.md) when deciding whether syntax or behavior is valid Zsh. Supplemental-tool acceptance is not language authority. Do not copy code-derived parser facts into this index.

For native packages, historical records, implementation and supporting files in this domain, use [repository resources](repository-resources.md). Each file has an imported source or retained-owner reference in the checked repository inventory.
