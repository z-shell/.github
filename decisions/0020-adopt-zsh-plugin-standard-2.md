# 20. Adopt Zsh Plugin Standard 2 as a Clean Portable Contract

- **Status:** PROPOSED
- **Date:** 2026-08-28
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

Zsh plugins share one shell namespace and one caller process. Repository-local
conventions for globals, helper functions, configuration, directories, and
cleanup therefore accumulate as ecosystem-wide maintenance cost. A user or
contributor should not need to learn a new declaration system for every plugin.

The public Zsh Plugin Standard now defines version 2 as a clean portable
contract. The organization must apply that contract consistently without
copying it into a second z-shell-only standard or treating Zi integration as a
portable requirement.

## Decision

Adopt version 2 of the canonical public
[Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
for maintained z-shell plugins and new plugin scaffolds.

1. The wiki remains the sole owner of the portable interoperability contract.
   Organization policy links to it and owns only z-shell adoption,
   verification, and migration requirements.
2. Each plugin documents one portable ASCII project identifier and derives
   every persistent shell-visible name from it.
3. Public declarative configuration uses one namespaced `zstyle` context.
   Project-owned parameters are private runtime state, not parallel public
   configuration.
4. Portable plugin code neither requires nor mutates shared manager or plugin
   registry parameters. Zi remains the reference manager, but Zi-specific
   behavior is an optional, independently tested profile.
5. A maintained plugin provides an idempotent, partial-load-safe unload
   function. Cleanup is ownership-aware: it restores a prior value only while
   the installed value remains unchanged and preserves newer user state.
6. Plugin repositories distinguish the authoritative entrypoint, private
   eagerly sourced `lib/`, autoloaded `functions/`, native `completions/`, and
   user-invoked `bin/` roles. Optional directories are omitted when unused.
7. Static analysis verifies structure and namespace rules. A clean-process
   runtime suite separately proves the declared load surface, repeated source,
   partial failure, hostile caller state, and exact unload behavior.
8. New scaffolds conform immediately. Maintained plugins migrate through
   owning issues. Refactored plugins do not retain legacy aliases, duplicate
   configuration variables, shared-registry writes, or alternate declaration
   systems merely for compatibility.
9. Required CI pins use exact released commits of the organization tools.
   Unreleased branches and pull-request commits are not substituted for a
   release pin.

## Consequences

### Positive

- Users see a predictable configuration, namespace, layout, and lifecycle.
- Contributors can transfer knowledge between plugin repositories.
- Static diagnostics and runtime lifecycle proof have distinct, testable jobs.
- Zi remains a useful reference integration without narrowing portability.

### Costs and risks

- Existing plugins need deliberate breaking migrations.
- Exact cleanup requires more tests than load-only smoke checks.
- Organization enforcement cannot become required until the corresponding
  zsh-lint and ZUnit releases exist.
- The wiki and organization surfaces must be reviewed together to prevent
  duplicated or contradictory rules.

## Alternatives considered

### Add a z-shell profile above a looser portable standard

Rejected because the desired practices are useful to all plugin authors. A
second organization contract would recreate the inconsistency this decision is
intended to remove.

### Preserve legacy interfaces indefinitely

Rejected because the maintained plugins are being refactored and compatibility
layers would retain duplicate state, naming, and configuration systems.

### Rely on static analysis alone

Rejected because static source cannot prove runtime restoration, partial-load
cleanup, or preservation of post-load user changes.

## References

- [z-shell/.github#557](https://github.com/z-shell/.github/issues/557)
- [Zsh Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard)
- `decisions/0002-zi-as-canonical-plugin-manager.md`
- `decisions/0009-testing-ci-strategy.md`
- `.github/instructions/zsh-plugin-standard.instructions.md`
- `.github/instructions/testing.instructions.md`
