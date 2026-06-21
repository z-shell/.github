---
name: zunit-test
description: Write and run ZUnit tests for Zsh plugins in this workspace. Use when the user asks to add tests for a plugin, write a .zunit test, or run the ZUnit suite. Covers ZUnit test syntax, the run/assert helpers, and the native test runner.
disable-model-invocation: true
---

# Write and run ZUnit tests

ZUnit (`repos/tools/zunit`) is the Zsh unit-testing framework used across the workspace. Tests live in a plugin's `tests/` directory as `*.zunit` files and run via the `zunit` CLI or the `test-native.yml` workflow.

## Test file shape

```zsh
#!/usr/bin/env zunit

@setup {
  # Runs before each @test — load the plugin under test here.
  load "../my-plugin.plugin.zsh"
}

@teardown {
  # Runs after each @test — call the unload function to reset state.
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

Cross-reference real examples in `repos/tools/zunit/tests/` and `repos/plugins/zsh-eza/tests/zsh-eza.zunit`.

## Running tests

From the plugin repo (requires `zunit` on PATH and a `.zunit.yml` config):

```sh
zunit                       # run the whole suite
zunit tests/my-plugin.zunit # run one file
```

CI runs them natively via the reusable workflow:
`uses: z-shell/zd/.github/workflows/test-native.yml@main` (accepts `zi_repo` / `zi_ref` inputs).

## Conventions

- Always pair `@setup` (load plugin) with `@teardown` (call `<plugin>_plugin_unload`) so tests don't leak state between cases.
- One behavior per `@test`; name it as a sentence describing the expected behavior.
- Keep `.zunit` files under the plugin's `tests/` directory.
