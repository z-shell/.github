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
   - One portable ASCII project identifier, for example `zsh_foo`. This owns
     every persistent public and private shell name and the
     `:zsh_foo:config` style context.

3. **Create the layout**. Create only the authoritative entrypoint initially.
   Add each optional directory only when its execution role is required:

   ```
     <target-repository-root>/
     <name>.plugin.zsh
     lib/          # optional private eager sources
     functions/    # optional autoload functions
     completions/  # optional native completion functions
     bin/          # optional user-invoked executables
   ```

4. **Write the entry file** from `templates/plugin.plugin.zsh`, replacing
   `__IDENTIFIER__` with the ASCII project identifier. Keep the modelines as the
   first two lines verbatim. Do not create shared `Plugins` state, scattered
   public configuration parameters, or a second legacy namespace. Add
   manager-specific behavior only when the user requests and identifies that
   optional profile, and keep it outside the portable contract.

5. **Write autoload function bodies**: begin each generated function body with
   `builtin emulate -L zsh`. Select only the correctness-affecting options that
   function needs. Apply `zsh/autoload/initialize`, `zsh/options/localize`, and
   the repository compatibility floor; do not copy a universal option bundle.

6. **Verify syntax and lifecycle**:
   - Run `zsh -f -n <name>.plugin.zsh` for native syntax validation under
     `zsh/validation/native-authority`.
   - In an isolated shell with temporary `HOME` and `ZDOTDIR`, prime the ZUnit
     lifecycle observer, snapshot the baseline, source the entry file, and
     assert the exact documented load allowlist.
   - Test repeated source, partial initialization failure, hostile caller
     options, non-interactive loading, and post-load user changes. Invoke
     `<identifier>_plugin_unload` and assert ownership-aware restoration.
   - Remove the temporary directory. `zsh -f` suppresses normal RCS processing,
     but a system `zshenv` may still execute.

7. **Report** the created tree, execution profiles, syntax result, lifecycle
   result, and any repository-floor decision.

## Canonical links for scaffold decisions

- Caller-state preservation: `zsh/sourced/preserve-caller-state`.
- Autoload body initialization: `zsh/autoload/initialize`.
- Stable namespace: `zsh/plugin/stable-namespace`.
- Coherent configuration: `zsh/plugin/coherent-configuration`.
- Documented plugin effects: `zsh/plugin/document-load-surface`.
- Owned-effect cleanup: `zsh/plugin/exact-lifecycle`.
- Controlled autoload paths: `zsh/security/trust-paths`.

Keep the rule rationale in the canonical instruction. The scaffold must reverse
every owned side effect and self-destruct; syntax success alone is not a
behavioral result. Pin zsh-lint and ZUnit only to commits from published
releases when wiring required CI.
