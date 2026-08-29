# 21. Derive Chroma Command Knowledge at Runtime

- **Status:** PROPOSED
- **Date:** 2026-08-29
- **Deciders:** ss-o
- **Supersedes:** None
- **Superseded by:** None

## Context

F-Sy-H chromas recognize command-line subcommands and options. Most existing
tables were copied from command help at one point in time. They have no owner
or automatic refresh mechanism, so they silently lose coverage as tools add or
rename commands. Git coverage demonstrates the problem: the detailed static
grammar covers a small subset of Git while the installed Git executable can
describe its complete current command surface.

Runtime discovery is not safe on the ZLE highlighting path when implemented as
a synchronous process. It can block every edit, execute an unintended shell
string, or repeatedly query a slow executable. The command-knowledge source
therefore has to share the asynchronous worker and cache boundary adopted for
other external chroma lookups.

## Decision

Use runtime-derived command knowledge as the canonical source for chromas when
the target tool exposes stable machine-readable or predictably structured help.

1. Each supported tool has a small provider that declares argv-only discovery
   commands and parses their output. Providers never use string evaluation.
2. Discovery runs only through the asynchronous chroma worker. The current or
   stale cache is returned immediately, one worker refreshes an expired key,
   and worker completion requests a new highlight. No provider may fork
   synchronously from the ZLE highlighting path.
3. Cache keys identify the provider and command scope. Expensive command and
   option discovery uses a 15-minute in-memory lifetime by default. Provider
   failure, missing executables, empty output, and timeout preserve the last
   usable result or the frozen fallback.
4. A conservative checked-in fallback supplies deterministic first paint and
   behavior when discovery is unavailable. It is a resilience boundary, not a
   second canonical command specification.
5. Provider output is untrusted. Parsers force a stable locale, admit only
   constrained command and option token grammars, ignore prose and unexpected
   layouts, and fall back when no valid records remain.
6. The first Git provider derives top-level commands from `git help -a`, aliases
   from `git config --get-regexp`, and per-command option spellings from
   `git <command> -h`. Standard error capture is explicit because Git writes
   short help there. Per-command probing is limited to Git's built-in command
   sections. External `git-*` commands and shell aliases are not executed by
   highlighting; ordinary aliases are probed only when they resolve to an
   already admitted built-in command.
7. Existing detailed grammar remains semantic enrichment for argument roles,
   repository-aware validation, and the frozen fallback. Runtime option sets
   augment a detailed grammar before its `NO_MATCH` rule, so newly added valid
   options gain coverage without weakening detection of unknown options.
8. Adding ordinary support for a newly reported command or option is a runtime
   data refresh. Hand-written grammar is justified only when maintainers choose
   richer semantic highlighting beyond the provider contract.
9. Tests must cover frozen fallback, fixture-derived additions and removals,
   parser rejection, cache refresh, and the real interactive worker callback.
   A fixture containing knowledge absent from the checked-in grammar is the
   drift proof: it must become recognized without editing that grammar.

## Consequences

### Positive

- Coverage follows the user's installed tool instead of a repository snapshot.
- New ordinary commands and options do not require copied definition tables.
- Slow or missing tools cannot block first paint or erase deterministic
  fallback behavior.
- Runtime drift is observable in fixture and interactive tests.
- Detailed static grammar can remain focused on semantic value rather than
  exhaustive spelling lists.

### Costs and risks

- Help formats are not formal APIs for every tool and require provider-specific
  parsers with fail-safe behavior.
- Each first unseen command can start one background process.
- Frozen fallback data can still age, although it no longer limits normal
  runtime coverage.
- Runtime-only options initially know spelling and explicit separators, but not
  every argument type or cross-option rule supplied by detailed grammar.
- Executables earlier in `PATH` control the discovered data. Strict token
  admission limits interpretation, but providers still execute the same tool
  the user asked F-Sy-H to highlight.

## Alternatives considered

### Read Zsh completion definitions

Deferred because completion functions encode rich knowledge but are executable
shell programs with context and side effects. Safely extracting data without
invoking completion machinery on the ZLE path needs a separate design.

### Generate from an external completion-spec repository

Rejected for this subsystem because it adds a vendoring, licensing, versioning,
and generator-drift dependency while still describing a different tool version
than the one the user runs.

### Keep hand-written tables as the canonical source

Rejected because prior multi-year drift shows that review alone does not keep
copied option inventories current.

## References

- [F-Sy-H issue 73](https://github.com/z-shell/F-Sy-H/issues/73)
- [F-Sy-H issue 68](https://github.com/z-shell/F-Sy-H/issues/68)
- `decisions/0009-testing-ci-strategy.md`
- `decisions/0015-zsh-scripting-standard.md`
