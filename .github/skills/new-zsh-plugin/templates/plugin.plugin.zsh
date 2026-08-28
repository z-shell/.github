# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Zsh Plugin Standard 2
# https://wiki.zshell.dev/community/zsh_plugin_standard
() {
  builtin emulate -L zsh

  typeset -r source_path="${${(M)1:#/*}:-$PWD/$1}"
  typeset -r plugin_dir=${source_path:a:h}

  # Source private eager helpers from "$plugin_dir/lib" only when required.
  # Keep setup-only functions local to this loader. Autoloaded functions and
  # completions belong in their documented directories and are not sourced.

  # Define the documented public functions and register only namespaced,
  # explicitly owned side effects here. Ordinary public configuration uses
  # the ':__IDENTIFIER__:config' zstyle context.

  __IDENTIFIER___plugin_unload() {
    builtin emulate -L zsh

    # Reverse each owned side effect explicitly. Restore prior state only while
    # the installed value remains unchanged, and preserve newer user state.
    builtin unfunction __IDENTIFIER___plugin_unload
  }
} "${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
