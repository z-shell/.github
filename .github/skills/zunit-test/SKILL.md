---
name: zunit-test
description: Use when a user asks to add tests for a Zsh plugin, write a .zunit test, or run a ZUnit suite.
disable-model-invocation: true
---

# Write and run ZUnit tests

ZUnit (`z-shell/zunit`) is the Zsh unit-testing framework used across Z-Shell
repositories. Its syntax and helpers are framework-specific, not a second Zsh
language standard.

## Establish the test contract

Before writing tests:

1. Read `.github/instructions/zsh-scripting.instructions.md` and
   `lib/zsh-standard-policy.json`.
2. Classify each `.zunit` source as `test-fixture` and name the production
   profile exercised by the fixture.
3. Isolate temporary `HOME` and `ZDOTDIR` under
   `zsh/test/isolate-environment`.
4. Load the subject the same way production does under
   `zsh/test/match-production-profile`.
5. Prime the plugin contract observer before the baseline, then test exact
   ownership-aware restoration under `zsh/plugin/exact-lifecycle`.

`zsh -f` is useful where applicable, but it does not prove every system startup
source was skipped; a system `zshenv` may still execute.

## Test file shape

The example below exercises a Standard 2 plugin with one documented public
function and its unload function.

```zsh
#!/usr/bin/env zunit

@setup {
  zunit_plugin_contract_prime
  zunit_plugin_contract_snapshot before
  load "../my-plugin.plugin.zsh"
  zunit_plugin_contract_snapshot loaded
}

@teardown {
  # A lifecycle test can already have invoked the self-destructing function.
  if (( ${+functions[my_plugin_plugin_unload]} )); then
    my_plugin_plugin_unload
  fi
}

@test 'load exposes only the documented surface' {
  assert before plugin_load_surface loaded \
    function:my_plugin_action \
    function:my_plugin_plugin_unload
}

@test 'repeated source is harmless' {
  load "../my-plugin.plugin.zsh"
  zunit_plugin_contract_snapshot repeated

  assert loaded plugin_restored repeated
}

@test 'unload restores owned state and self-destructs' {
  zunit_plugin_contract_snapshot user_state
  my_plugin_plugin_unload
  zunit_plugin_contract_snapshot after

  assert before plugin_unloaded loaded user_state after
}

@test 'descriptive name of the behavior' {
  run my_function arg1 arg2

  assert $state equals 0
  assert "$output" same_as 'expected output'
}
```

## Key helpers

- `run <cmd>` — execute a command; populates `$state` (exit code), `$output` (combined output), `$lines` (array).
- Assertions: `assert $state equals 0`, `assert "$output" same_as '...'`, `assert "$output" is_empty`, `assert "$x" contains '...'`, `assert "$path" is_file`, `assert "$x" matches '<regex>'`.
- A test file may define one `@setup` and one `@teardown`, each running around every test in that file.
- Result helpers tests can assert against: `pass`, `fail '<msg>'` (state 1), `error '<msg>'` (state 78), `skip '<msg>'` (state 48).

Cross-reference real examples in `z-shell/zunit:tests/` and
`z-shell/zsh-eza:tests/zsh-eza.zunit`.

Add explicit lifecycle tests for each declared side effect. Test partial
initialization failure, hostile caller options, non-interactive loading, and a
post-load user change. Assert that unload removes only plugin-owned state,
restores pre-load state only when still owned, preserves the user's newer state,
and self-destructs. Portable fixtures do not create or mutate a shared
`Plugins` parameter.

Declare each intentional negative fixture in repository metadata under
`zsh/test/declare-negative-fixtures`. Name the exact fixture and expected
failure mode; do not exclude an entire tests directory.

## Running tests

From the plugin repository (requires `zunit` on `PATH` and a `.zunit.yml`
configuration):

```sh
zunit                       # run the whole suite
zunit tests/my-plugin.zunit # run one file
```

Follow the canonical GitHub Actions policy when wiring CI. Pin ZUnit only to an
exact commit from a published release. Do not copy a mutable reusable-workflow
reference or an unreleased pull-request commit.

## Conventions

- Pair `@setup` production-equivalent loading with `@teardown` cleanup. Assert
  post-unload state rather than only invoking the unload function.
- Keep one behavior per `@test`; name it as a sentence describing the expected
  behavior.
- Keep `.zunit` files under the plugin's `tests/` directory.
