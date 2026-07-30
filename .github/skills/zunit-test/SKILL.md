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
5. Test unload and actual restoration under `zsh/plugin/restore-state`.

`zsh -f` is useful where applicable, but it does not prove every system startup
source was skipped; a system `zshenv` may still execute.

## Test file shape

```zsh
#!/usr/bin/env zunit

@setup {
  # Runs before each @test; load the plugin as production does.
  load "../my-plugin.plugin.zsh"
}

@teardown {
  # Runs after each @test; call unload and verify restoration in a test.
  my-plugin_plugin_unload 2>/dev/null
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
- Lifecycle blocks: `@setup`, `@teardown`, plus file-level `@setup`/`@teardown` if defined once.
- Result helpers tests can assert against: `pass`, `fail '<msg>'` (state 1), `error '<msg>'` (state 78), `skip '<msg>'` (state 48).

Cross-reference real examples in `z-shell/zunit:tests/` and
`z-shell/zsh-eza:tests/zsh-eza.zunit`.

Add explicit lifecycle tests for each declared side effect. Assert that unload
removes only plugin-owned state, preserves pre-existing state, removes the
`Plugins` key, and self-destructs.

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

CI runs them natively via the reusable workflow:
`uses: z-shell/zd/.github/workflows/test-native.yml@main` (accepts `zi_repo` / `zi_ref` inputs).

## Conventions

- Pair `@setup` production-equivalent loading with `@teardown` cleanup, and
  assert the post-unload state rather than only invoking unload.
- Keep one behavior per `@test`; name it as a sentence describing the expected
  behavior.
- Keep `.zunit` files under the plugin's `tests/` directory.
