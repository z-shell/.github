---
name: new-zsh-plugin
description: Use when a user asks to create a new Zsh plugin, start a plugin from scratch, or add a plugin skeleton.
disable-model-invocation: true
---

# Create a new Zsh plugin

Scaffold against the canonical Zsh standard and the owning repository's local
contract. The skill supplies plugin-specific procedure, not independent Zsh
semantics.

## Steps

1. **Read context and classify**:
   - Read `.github/instructions/zsh-scripting.instructions.md` and
     `lib/zsh-standard-policy.json` first.
   - Read root `AGENTS.md` and the owning repository's local `AGENTS.md` when
     present.
   - Identify the repository compatibility floor.
   - Select `sourced-library` for the plugin entry point and
     `autoload-function` for files beneath `functions/`.

2. **Gather inputs** (ask only if not supplied):
   - An explicit target repository root. The caller must supply it; do not infer
     or default to a multi-repository checkout path.
   - Plugin name in kebab-case, for example `zsh-foo` with entry file
     `zsh-foo.plugin.zsh`.

3. **Create the layout**:

   ```
   <target-repository-root>/
     <name>.plugin.zsh
     functions/
     lib/
     docs/
   ```

4. **Write the entry file** from `templates/plugin.plugin.zsh`, replacing
   `__NAME__` (kebab name) and `__FPATH_VAR__` (an upper-snake project-owned
   parameter such as `ZSH_FOO_FPATH`). Keep the modelines as the first two lines
   verbatim. The first source owns the `fpath` decision; repeated sources must
   not reset it. Add manager-specific registration only when the user requests
   and identifies that optional profile.

5. **Write autoload function bodies**: begin each generated function body with
   `builtin emulate -L zsh`. Select only the correctness-affecting options that
   function needs. Apply `zsh/autoload/initialize`, `zsh/options/localize`, and
   the repository compatibility floor; do not copy a universal option bundle.

6. **Verify syntax and lifecycle**:
   - Run `zsh -f -n <name>.plugin.zsh` for native syntax validation under
     `zsh/validation/native-authority`.
   - In an isolated shell with temporary `HOME` and `ZDOTDIR`, source the entry
     file, verify its declared load effects, invoke `<name>_plugin_unload`, and
     assert post-unload restoration of `fpath`, scaffold parameters, functions,
     hooks, aliases, options, and every other declared side effect.
   - The scaffold removes the last exact `fpath` match that it appended. Do not
     insert or reorder an indistinguishable equal entry after that append
     before unloading; Zsh arrays do not retain occurrence identity.
   - Remove the temporary directory. `zsh -f` suppresses normal RCS processing,
     but a system `zshenv` may still execute.

7. **Report** the created tree, execution profiles, syntax result, lifecycle
   result, and any repository-floor decision.

## Canonical links for scaffold decisions

- Caller-state preservation: `zsh/sourced/preserve-caller-state`.
- Autoload body initialization: `zsh/autoload/initialize`.
- Documented plugin effects: `zsh/plugin/document-global-state`.
- Owned-effect cleanup: `zsh/plugin/restore-state`.
- Controlled autoload paths: `zsh/security/trust-paths`.

Keep the rule rationale in the canonical instruction. The scaffold must reverse
every owned side effect and self-destruct; syntax success alone is not a
behavioral result.
