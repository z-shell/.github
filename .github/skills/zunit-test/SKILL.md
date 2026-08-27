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
5. When unload is part of the subject's contract, test actual restoration under
   `zsh/plugin/restore-state`.

`zsh -f` is useful where applicable, but it does not prove every system startup
source was skipped; a system `zshenv` may still execute.

## Test file shape

The example below exercises a subject that declares an unload contract and an
optional `Plugins` registration. Omit those parts when the subject declares
neither behavior.

```zsh
#!/usr/bin/env zunit

typeset -ga saved_fpath

@setup {
  # Runs before each @test; load the plugin as production does.
  saved_fpath=("${fpath[@]}")
  typeset -gA Plugins
  unset 'Plugins[MY_PLUGIN]'
  load "../my-plugin.plugin.zsh"
}

@teardown {
  # A lifecycle test can already have invoked the self-destructing function.
  if (( ${+functions[my-plugin_plugin_unload]} )); then
    my-plugin_plugin_unload
  fi
}

@test 'unload restores state and self-destructs' {
  my-plugin_plugin_unload

  assert "${(j:|:)fpath}" same_as "${(j:|:)saved_fpath}"
  assert "${+Plugins[MY_PLUGIN]}" equals 0
  assert "${+functions[my-plugin_plugin_unload]}" equals 0
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

When unload is part of the subject's contract, add explicit lifecycle tests for
each declared side effect. Assert that unload removes only plugin-owned state,
restores any registered `Plugins` key to its pre-load state, and
self-destructs. Test absent and existing key states when the plugin registers
one. Omit unload-specific fixtures for subjects without that contract.

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

Follow the canonical GitHub Actions policy when wiring CI. Do not copy a mutable
reusable-workflow reference; select an immutable ref only after its owning
rollout has approved and published one.

## Conventions

- Pair `@setup` production-equivalent loading with `@teardown` cleanup. When
  unload is part of the contract, assert post-unload state rather than only
  invoking the unload function.
- Keep one behavior per `@test`; name it as a sentence describing the expected
  behavior.
- Keep `.zunit` files under the plugin's `tests/` directory.
