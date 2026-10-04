# Modules

Select this domain for compiled Zsh modules and native library integration. Build configuration, ABI assumptions and supported platforms belong to the owning repository.

| Task | Authoritative context |
| --- | --- |
| Inspect module source and supported build/runtime contracts | [zpmod](https://github.com/z-shell/zpmod) or the actual module repository's instructions and build files |
| Select a controlled build/runtime environment | [Controlled validation](../quality/controlled-validation.md) and [zd integration](../quality/zd-validation.md) |
| Choose release validation | [Testing contract](../quality/testing.md) and [release procedure](../governance/release.md) |

Use [Zsh](../zsh/index.md) for language-facing behavior. A container result does not establish native-platform compatibility; record the actual runtime, architecture and toolchain from the owning checks.
