---
description: "Canonical Zsh authoring, review, compatibility, safety, and validation standard"
applyTo: "**/*.zsh,**/*.plugin.zsh,**/*.zsh-theme,**/*.zunit,**/.zshenv,**/.zprofile,**/.zshrc,**/.zlogin,**/.zlogout,**/zshenv,**/zprofile,**/zshrc,**/zlogin,**/zlogout,**/functions/**,**/completions/**/_*"
---

# Zsh Scripting Standard

## Purpose, scope, and semantic authority

This instruction is the canonical normative prose for Zsh authoring, review,
diagnosis, and modification across z-shell repositories. The released official
Zsh manual is the semantic authority. Organization policy controls repository
scope, compatibility evidence, source classification, and enforcement.

The machine-readable counterpart is `lib/zsh-standard-policy.json`. Its stable
rule identifiers, metadata, source-classification globs, and release record must
remain synchronized with this instruction.

## How to apply the standard

Classify the actual dialect before applying any language rule. Then identify the
repository compatibility floor and select exactly one execution profile.
Evaluate every rule whose profile list includes that selection. `required`
rules are mandatory, `recommended` rules are the default absent contrary
evidence, and `review` rules require focused human judgment.

Phase 1 defines the classifier contract but does not claim that a classifier is
implemented or active. Until classifier delivery, use the recorded evidence
manually and fail rather than guess when evidence conflicts.

## Execution-profile selection

The five profiles are:

- `standalone-executable`: a directly invoked Zsh program that owns initial
  state;
- `startup-file`: a Zsh startup or shutdown file read for a defined shell
  lifecycle phase that may make phase-owned effects;
- `sourced-library`: a plugin or library loaded into caller state;
- `autoload-function`: an autoloaded function body, including completions;
- `test-fixture`: a test or fixture evaluated under an explicit production
  profile.

The official [Startup/Shutdown Files chapter](https://zsh.sourceforge.io/Doc/Release/Files.html)
defines these lifecycle phases. Unlike a caller-preserving `sourced-library`,
a `startup-file` may make phase-owned effects without being required to
configure or change shell state.

Path is evidence, not sole authority. Use path, basename, shebang, invocation,
repository override, and actual behavior together. Ambiguous or unassigned
sources are errors.

## Compatibility and repository-floor model

The policy records Zsh 5.9.2 as the reviewed stable release, not as a universal
minimum. Each repository must provide its own evidence-backed compatibility
floor. A version-sensitive rule needs the first supported release plus either a
compatible floor, a tested compatibility branch, or a deliberate approved floor
increase.

`minimum_zsh: null` means a Phase 1 rule is not identified as
version-sensitive. It does not claim support for every historical Zsh release.

## Normative-rule notation

Each H3 rule heading is a stable rule ID. The six metadata lines are normative
and mirror the JSON rule object in order:

- Level
- Profiles
- Minimum Zsh
- Basis
- Evidence
- Enforcement

Evidence IDs resolve to the official documentation reference index. Enforcement
describes the applicable layer, not a claim that every listed layer is already
implemented.

## Dialect and context

### `zsh/authority/released-manual`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `manual-index`, `release-notes`
- Enforcement: `human-review`

Resolve language semantics against the relevant released official manual before
organization policy, examples, or tools.

### `zsh/compatibility/respect-floor`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`, `release-notes`
- Enforcement: `human-review`

Identify the repository compatibility floor before using or recommending
version-sensitive behavior.

### `zsh/compatibility/annotate-version-sensitive`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `manual-index`, `release-notes`
- Enforcement: `human-review`

Record the first supported release for version-sensitive rules and require a
compatible floor, tested branch, or deliberate floor increase.

### `zsh/context/classify`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `shell-grammar`
- Enforcement: `classifier`, `human-review`

Classify actual dialect from path, shebang, invocation, and repository override
before applying rules.

### `zsh/context/select-profile`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `shell-grammar`, `functions`
- Enforcement: `classifier`, `human-review`

Select one of the five execution profiles before assessing options, scope, or
caller state.

### `zsh/context/no-cross-dialect-defaults`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-grammar`, `expansion`
- Enforcement: `human-review`

Do not import Bash or POSIX defaults into native Zsh.

## Read, review, diagnosis, and modification scope

### `zsh/review/report-without-rewrite`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`
- Enforcement: `human-review`

Report relevant violations and consequences during read-only work without
silently rewriting unrelated legacy code.

### `zsh/change/conform-touched-code`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`
- Enforcement: `human-review`

New and materially changed code follows required rules. Broad cleanup or
compatibility-floor changes require separate scope.

## Standalone executables

### `zsh/standalone/initialize`

- Level: `required`
- Profiles: `standalone-executable`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `shell-builtins`, `options`
- Enforcement: `native-syntax`, `runtime-test`, `human-review`

Use a deliberate Zsh shebang, establish native state with `emulate -R zsh`,
and declare correctness-affecting options before dependent logic.

```zsh
#!/usr/bin/env zsh
emulate -R zsh
setopt pipe_fail
```

`emulate -R zsh` resets settable option state to native Zsh defaults, subject
to documented exceptions; it does not clear other startup-file effects.
Reusable functions instead begin with `builtin emulate -L zsh` to localize
their state.

### `zsh/standalone/no-startup-state`

- Level: `required`
- Profiles: `standalone-executable`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `options`, `shell-grammar`
- Enforcement: `runtime-test`

Do not rely on caller aliases, functions, interactive options, or user startup
state.

## Sourced libraries and plugin entry points

### `zsh/sourced/preserve-caller-state`

- Level: `required`
- Profiles: `sourced-library`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `functions`, `options`, `parameters`
- Enforcement: `runtime-test`, `human-review`

Sourced top level preserves caller options, traps, directories, descriptors,
hooks, widgets, aliases, parameters, and search paths except for documented
plugin effects.

Do not use top-level `emulate -L zsh` as isolation. `-L` localizes state only
for the surrounding function, so at sourced top level it can still alter the
caller. Put option-sensitive work inside an immediately executed anonymous
function:

```zsh
() {
  builtin emulate -L zsh
  setopt local_options
  # Reusable work.
}
```

## Autoload functions and completions

### `zsh/autoload/initialize`

- Level: `required`
- Profiles: `autoload-function`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `functions`, `shell-builtins`, `options`
- Enforcement: `lint`, `runtime-test`

Begin executable function-body logic with `builtin emulate -L zsh`. Only a
narrowly justified early-return guard may precede it.

### `zsh/autoload/suppress-alias-expansion`

- Level: `recommended`
- Profiles: `autoload-function`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `functions`, `shell-builtins`
- Enforcement: `human-review`

At the loader, select the declared autoload file form. For a bare Zsh-style
function body, normally use `autoload -Uz name` so loading selects Zsh form and
suppresses alias expansion. Compile autoload artifacts with `zcompile -U -z`:
`-U` records alias suppression and `-z` records Zsh file style. Without
`zcompile -z` or `zcompile -k`, loading consults the runtime `KSH_AUTOLOAD`
setting; a style recorded in the compiled artifact overrides later `autoload`
flags.

### `zsh/completion/preserve-trust-boundaries`

- Level: `required`
- Profiles: `startup-file`, `autoload-function`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `completion-system`, `functions`
- Enforcement: `runtime-test`, `human-review`

When a startup file initializes completion or autoloaded completion code runs,
treat `fpath`, completion-directory permissions, modules, and completion
dependencies as trust boundaries. Never bypass `compinit` or `compaudit`
security behavior.

## Tests and fixtures

### `zsh/test/isolate-environment`

- Level: `required`
- Profiles: `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `shell-grammar`, `options`
- Enforcement: `runtime-test`

Run behavior with isolated `HOME` and `ZDOTDIR`. Use `zsh -f` where applicable,
and remember that a system `zshenv` may still execute.

### `zsh/test/declare-negative-fixtures`

- Level: `required`
- Profiles: `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `shell-grammar`
- Enforcement: `classifier`

Mark intentionally invalid, legacy, or lint-negative fixtures in repository
metadata instead of excluding an entire test directory.

### `zsh/test/match-production-profile`

- Level: `required`
- Profiles: `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `functions`, `options`
- Enforcement: `runtime-test`

Test load, unload, restoration, and compatibility under the production
execution profile.

## Options and emulation

### `zsh/options/declare-correctness-state`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `options`
- Enforcement: `runtime-test`, `human-review`

Set or unset every correctness-affecting non-default option instead of
inheriting unknown state.

### `zsh/options/localize`

- Level: `required`
- Profiles: `startup-file`, `sourced-library`, `autoload-function`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-builtins`, `options`
- Enforcement: `lint`, `runtime-test`

Place option-sensitive reusable work in a function beginning with
`builtin emulate -L zsh`. `-L` localizes most options, pattern-disable state,
and signal traps in the surrounding function. `PRIVILEGED` and `RESTRICTED`
are documented option exceptions. When `POSIX_TRAPS` is set, `LOCAL_TRAPS`
does not localize an `EXIT` trap. Handle these exceptions explicitly; `-L`
does not make a sourced top level safe.

For `startup-file`, this rule governs reusable function bodies and temporary
function-local work, not intentional top-level lifecycle effects.

### `zsh/options/no-top-level-leak`

- Level: `required`
- Profiles: `sourced-library`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `options`, `functions`
- Enforcement: `runtime-test`

Do not change options, pattern state, or traps at sourced top level.

### `zsh/options/no-blanket-error-mode`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `options`, `shell-grammar`
- Enforcement: `human-review`

Do not prescribe blanket `set -euo pipefail`. Choose and test `ERR_EXIT`,
`ERR_RETURN`, `NO_UNSET`, and `PIPE_FAIL` for the actual profile. These options
have Zsh-specific control-flow consequences and do not form a universal safety
bundle.

### `zsh/options/constrain-multios`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `redirection`, `options`
- Enforcement: `runtime-test`

Constrain or disable `MULTIOS` when implicit fan-out is not intended.

## Parameters, arrays, and scope

### `zsh/parameters/declare-scope`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`, `shell-builtins`
- Enforcement: `lint`

Declare function-local parameters and intentional globals explicitly.

### `zsh/parameters/avoid-special-name-collisions`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`
- Enforcement: `lint`, `human-review`

Do not repurpose a Zsh special parameter name for unrelated local or scratch
data. Check the Special Parameters inventory before declaring a new name. For
example, `status` is read-only, and `path` is tied to `PATH`; assignment can
fail or change command lookup. Use purpose-specific names such as
`command_status` and `candidate_paths`.

### `zsh/parameters/account-dynamic-scope`

- Level: `review`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`, `functions`
- Enforcement: `human-review`

Account for dynamic scope when a called function can observe caller-local
parameters.

### `zsh/arrays/declare-kind`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`
- Enforcement: `lint`

Declare indexed and associative arrays explicitly.

```zsh
typeset -a indexed
typeset -A associative
```

### `zsh/arrays/native-indexing`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`
- Enforcement: `lint`

Use native one-based indexing unless a documented and tested compatibility
profile requires otherwise.

## Expansion, quoting, and patterns

### `zsh/expansion/preserve-boundaries`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `expansion`, `parameters`
- Enforcement: `lint`, `runtime-test`

Choose scalar or array expansion forms that deliberately preserve elements and
empty values.

```zsh
typeset -a values=( "one value" "" three )
print -rl -- "${values[@]}"
```

### `zsh/expansion/use-native-word-splitting`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `expansion`
- Enforcement: `lint`

Do not assume Bash or POSIX implicit word splitting. Request splitting only when
intended.

### `zsh/quoting/quote-boundaries`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `expansion`, `redirection`
- Enforcement: `lint`

Quote command arguments, assignments, and redirection targets according to
native Zsh expansion semantics.

### `zsh/associative/deterministic-order`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `parameters`, `expansion`
- Enforcement: `runtime-test`

Sort associative keys explicitly when output order is observable.

### `zsh/patterns/declare-interpretation`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `expansion`, `conditional-expressions`
- Enforcement: `lint`, `human-review`

Make literal, glob-pattern, POSIX regular-expression, and PCRE interpretation
explicit. In `[[ ... ]]`, quoting changes pattern treatment:

```zsh
[[ $value == "$literal" ]]
[[ $value == ${~pattern} ]]
```

## Conditions and arithmetic

### `zsh/conditions/use-native-form`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `conditional-expressions`
- Enforcement: `lint`

Prefer native `[[ ... ]]` for Zsh conditions.

### `zsh/conditions/declare-match-mode`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `conditional-expressions`
- Enforcement: `lint`, `human-review`

Document and encode the intended comparison or match mode.

### `zsh/arithmetic/handle-zero-status`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `arithmetic-evaluation`
- Enforcement: `lint`, `runtime-test`

Account for `(( ... ))` returning nonzero when its expression evaluates to
zero:

```zsh
(( count = 0 )) || true
```

The assignment succeeds semantically but the arithmetic command status is 1.

### `zsh/arithmetic/validate-input`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `arithmetic-evaluation`, `parameters`
- Enforcement: `runtime-test`, `human-review`

Validate externally supplied arithmetic and subscript input before evaluation.

### `zsh/arithmetic/declare-base`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `arithmetic-evaluation`
- Enforcement: `human-review`

Make numeric type and base assumptions explicit.

## Status, pipelines, traps, and cleanup

### `zsh/status/check-critical`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `shell-grammar`, `shell-builtins`
- Enforcement: `lint`, `runtime-test`

Handle critical statuses explicitly instead of relying only on automatic exit
options.

### `zsh/status/check-pipeline-components`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-grammar`, `parameters`
- Enforcement: `lint`, `runtime-test`

Inspect `$pipestatus` when every pipeline component matters:

```zsh
producer | consumer
typeset -a statuses=( "${pipestatus[@]}" )
(( ${statuses[1]} == 0 && ${statuses[2]} == 0 ))
```

### `zsh/status/preserve-command-substitution`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-grammar`, `shell-builtins`
- Enforcement: `lint`, `runtime-test`

Separate a status-sensitive command substitution assignment from declaration
forms that replace its status. In a function or sourced context:

```zsh
typeset value
value=$(critical_command) || return
```

At a standalone top level, use `exit` or another explicit top-level failure
handler:

```zsh
typeset value
value=$(critical_command) || exit
```

### `zsh/cleanup/scope-traps`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `functions`, `shell-grammar`
- Enforcement: `runtime-test`

Declare trap form and scope, and restore caller trap state where required.

### `zsh/cleanup/use-always`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-grammar`
- Enforcement: `runtime-test`, `human-review`

Prefer `{ try-list } always { cleanup }` when its documented control flow
matches the cleanup requirement.

## Input, output, redirection, and descriptors

### `zsh/output/literal-vs-formatted`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-builtins`
- Enforcement: `lint`

Use `print -r --` for literal native-Zsh output and `printf` for formatted
output:

```zsh
print -r -- "$literal"
printf '%s: %d\n' "$label" "$count"
```

### `zsh/input/raw-mode`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-builtins`
- Enforcement: `lint`, `runtime-test`

Use raw input modes when backslash interpretation is not intended.

### `zsh/operands/end-options`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `shell-builtins`
- Enforcement: `lint`

Place `--` before untrusted operands when the builtin supports it.

### `zsh/redirection/order-and-quote`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `redirection`, `expansion`
- Enforcement: `lint`, `human-review`

Quote redirection targets and make descriptor order deliberate.

### `zsh/fd/close-allocated`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `redirection`, `parameters`
- Enforcement: `lint`, `runtime-test`

Close parameter-allocated descriptors explicitly:

```zsh
exec {output_fd}>| "$output_path"
print -u "$output_fd" -r -- "$value"
exec {output_fd}>&-
```

## Security and trust boundaries

### `zsh/security/treat-strings-as-data`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `expansion`, `parameters`
- Enforcement: `lint`, `human-review`

Keep untrusted strings as data and avoid implicit code, pattern, arithmetic,
option, or path interpretation.

### `zsh/security/no-unreviewed-reevaluation`

- Level: `review`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `expansion`, `shell-builtins`
- Enforcement: `human-review`

Require focused security review for `eval`, `${(e)...}`, executable glob
qualifiers, and generated code.

### `zsh/security/no-restricted-shell-sandbox`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`
- Minimum Zsh: `null`
- Basis: `language-semantics`
- Evidence: `restricted-shell`
- Enforcement: `human-review`

Never present restricted-shell mode as a security sandbox.

### `zsh/security/trust-paths`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `command-execution`, `shell-builtins`, `functions`, `completion-system`
- Enforcement: `runtime-test`, `human-review`

Trust only controlled executable search paths (`$path`), autoload search paths
(`fpath`), module search paths (`$module_path`), and completion directories.

### `zsh/security/no-passive-network`

- Level: `required`
- Profiles: `sourced-library`, `autoload-function`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `functions`
- Enforcement: `runtime-test`

Plugin and completion load paths perform no implicit network activity.

## Plugin lifecycle and documentation

### `zsh/plugin/document-global-state`

- Level: `required`
- Profiles: `sourced-library`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `parameters`, `functions`
- Enforcement: `human-review`

Document every intentional global parameter, hook, widget, alias, function,
option, path, descriptor, and directory effect.

### `zsh/plugin/restore-state`

- Level: `required`
- Profiles: `sourced-library`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `functions`, `parameters`, `options`
- Enforcement: `runtime-test`, `human-review`

When unload is part of the contract, reverse every owned side effect and remove
the unload function.

### `zsh/documentation/comment-invariants`

- Level: `recommended`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`
- Enforcement: `human-review`

Comment non-obvious intent, invariants, trust boundaries, compatibility
decisions, and accepted parser gaps, not visible syntax.

### `zsh/documentation/track-deferred-work`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`
- Enforcement: `human-review`

Link meaningful deferred semantic or parser work to an owning issue or tracker
item.

## Validation and tool boundaries

### `zsh/validation/native-authority`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `manual-index`, `shell-grammar`, `options`, `shell-builtins`
- Enforcement: `native-syntax`, `human-review`

Distinguish native-invalid Zsh from supplemental-tool limitations and treat
released Zsh as syntax authority.

`zsh -f -n` is native syntax validation, not behavioral validation. `zcompile`
may add a native compilation check only when output is written beneath temporary
storage and removed. Behavior, caller-state restoration, and compatibility
require runtime tests.

### `zsh/validation/no-shellcheck`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `shell-grammar`
- Enforcement: `classifier`

Do not send classified Zsh sources to ShellCheck or cite ShellCheck as Zsh
validation. ShellCheck does not validate Zsh. ShellCheck issue 809 may be linked
only as supplemental tool-boundary evidence, never as language authority.

### `zsh/validation/parser-gap`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `mixed`
- Evidence: `manual-index`
- Enforcement: `human-review`

Preserve a native-valid reproducer and report the tool gap when a supplemental
parser rejects released-valid Zsh:

```text
Native check: zsh -f -n fixture.zsh passes
Supplemental tool: record the pinned tool and failure
Disposition: keep the minimized fixture and link the owning issue
```

The `mvdan/sh` Zsh parser documentation may be linked only as supplemental
tool-boundary evidence, never as language authority. `zsh-lint` is supplemental
and must be pinned before gating.

### `zsh/formatting/no-unproven-rewrite`

- Level: `required`
- Profiles: `standalone-executable`, `startup-file`, `sourced-library`, `autoload-function`, `test-fixture`
- Minimum Zsh: `null`
- Basis: `organization-policy`
- Evidence: `manual-index`
- Enforcement: `human-review`

Do not apply automated Zsh rewrites until a reviewed fixture corpus proves the
transformation safe for that source class. `shfmt` remains check-only and
opt-in until that corpus proves its transformations safe. Native-valid
supplemental-parser gaps require a minimized fixture and owning issue rather
than a source rewrite.

## Official documentation reference index

- `manual-index`: [Zsh 5.9.2 Manual](https://zsh.sourceforge.io/Doc/Release/index.html)
- `release-notes`: [Zsh Release Notes](https://zsh.sourceforge.io/releases.html)
- `shell-grammar`: [Shell Grammar](https://zsh.sourceforge.io/Doc/Release/Shell-Grammar.html)
- `redirection`: [Redirection](https://zsh.sourceforge.io/Doc/Release/Redirection.html)
- `shell-builtins`: [Shell Builtin Commands](https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html)
- `options`: [Options](https://zsh.sourceforge.io/Doc/Release/Options.html)
- `parameters`: [Parameters](https://zsh.sourceforge.io/Doc/Release/Parameters.html)
- `expansion`: [Expansion](https://zsh.sourceforge.io/Doc/Release/Expansion.html)
- `conditional-expressions`: [Conditional Expressions](https://zsh.sourceforge.io/Doc/Release/Conditional-Expressions.html)
- `arithmetic-evaluation`: [Arithmetic Evaluation](https://zsh.sourceforge.io/Doc/Release/Arithmetic-Evaluation.html)
- `functions`: [Functions](https://zsh.sourceforge.io/Doc/Release/Functions.html)
- `completion-system`: [Completion System](https://zsh.sourceforge.io/Doc/Release/Completion-System.html)
- `restricted-shell`: [Restricted Shell](https://zsh.sourceforge.io/Doc/Release/Restricted-Shell.html)
- `command-execution`: [Command Execution](https://zsh.sourceforge.io/Doc/Release/Command-Execution.html)
