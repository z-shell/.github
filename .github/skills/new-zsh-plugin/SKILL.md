---
name: new-zsh-plugin
description: Scaffold a new Z-Shell-Standard-compliant Zsh plugin. Use when the user asks to create a new Zsh plugin, start a plugin from scratch, or add a plugin skeleton. Generates a compliant entry file (modeline, ZERO handling, capability-aware fpath setup, unload function) plus functions/ and docs/ layout.
disable-model-invocation: true
---

# Create a new Zsh plugin

Scaffold a plugin that conforms to the [Z-Shell Plugin Standard](https://wiki.zshell.dev/community/zsh_plugin_standard), `z-shell/.github/AGENTS.md`, and the owning repository's local `AGENTS.md` when present.

Official Zsh documentation is authoritative for shell semantics. The scaffold
honors the optional `PMSPEC` capability signal without requiring a shared
manager registry.

## Steps

1. **Gather inputs** (ask only if not supplied):
   - An explicit target repository root. The caller must supply it; do not infer
     or default to a multi-repository checkout path.
   - Plugin name in kebab-case, e.g. `zsh-foo` → entry file `zsh-foo.plugin.zsh`.

2. **Create the layout**:

   ```
   <target-repository-root>/
     <name>.plugin.zsh
     functions/
     lib/
     docs/
   ```

3. **Write the entry file** from `templates/plugin.plugin.zsh`, replacing
   `__NAME__` (kebab name) and `__FPATH_VAR__` (a namespaced upper-snake
   parameter such as `ZSH_FOO_FPATH`). Keep the modeline as the first two lines
   verbatim.

4. **Verify**: run `zsh -n <name>.plugin.zsh`. It must pass before reporting done. Source it in a subshell to confirm the unload function is defined:

   ```sh
   zsh -ic 'source ./<name>.plugin.zsh; (( ${+functions[<name>_plugin_unload]} )) && echo unload-ok'
   ```

5. **Report** the created tree and remind the user to fill in `functions/` (autoloaded, strict-emulation header) and `lib/` (sourced) as needed.

## Conventions to honor

- The entry file's first two lines are the required modeline.
- Autoloaded files under `functions/` must begin with:
  ```zsh
  builtin emulate -L zsh ${=${options[xtrace]:#off}:+-o xtrace}
  builtin setopt extended_glob warn_create_global typeset_silent no_short_loops rc_quotes no_auto_pushd
  ```
- The unload function must reverse **every** side effect and self-destruct.
- Namespace plugin-owned state, scope option changes, and perform no network
  activity during load.
- Keep portable behavior usable without optional manager capabilities. Track
  whether the plugin changed shared state so unload preserves manager- or
  user-owned state.
- No build system — verify by sourcing in a Zsh session, not by running a build.
