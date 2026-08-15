# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Zsh Plugin Standard
# https://wiki.zshell.dev/community/zsh_plugin_standard#zero-handling
() {
  builtin emulate -L zsh

  typeset -r source_path="${${(M)1:#/*}:-$PWD/$1}"
  typeset -r plugin_dir=${source_path:h}
  typeset -r functions_dir=$plugin_dir/functions

  # https://wiki.zshell.dev/community/zsh_plugin_standard#standard-plugins-hash
  typeset -gA Plugins

  # https://wiki.zshell.dev/community/zsh_plugin_standard#functions-directory
  # Canonical rule: zsh/security/trust-paths
  # The first source owns the persistent path and pre-load Plugins snapshot.
  # Re-sourcing must not reset either ownership record.
  if (( ! ${+parameters[__FPATH_VAR__]} )); then
    typeset -g __FPATH_VAR__=$functions_dir
    typeset -gi __FPATH_VAR___ADDED=0
    typeset -gi \
      __FPATH_VAR___PLUGINS_KEY_EXISTED=${+Plugins[__KEY__]}
    typeset -g \
      __FPATH_VAR___PLUGINS_KEY_VALUE=${Plugins[__KEY__]-}

    if [[ ${PMSPEC-} != *f* ]] &&
      (( ${fpath[(Ie)${__FPATH_VAR__}]} == 0 )); then
      fpath+=("${__FPATH_VAR__}")
      __FPATH_VAR___ADDED=1
    fi
  fi

  Plugins[__KEY__]=${__FPATH_VAR__:h}

  # --- Plugin body -----------------------------------------------------------
  # Source library files or autoload functions here, e.g.:
  #   source "$plugin_dir/lib/setup.zsh"
  #   autoload -Uz +X .__NAME__ && .__NAME__
  # Pair every added side effect with its exact cleanup in the unload function.

  # https://wiki.zshell.dev/community/zsh_plugin_standard#unload-function
  # Canonical rule: zsh/plugin/restore-state
  __NAME___plugin_unload() {
    builtin emulate -L zsh

    typeset -r functions_dir=${__FPATH_VAR__-}
    integer added=${__FPATH_VAR___ADDED:-0}
    integer key_existed=${__FPATH_VAR___PLUGINS_KEY_EXISTED:-0}
    typeset key_value=${__FPATH_VAR___PLUGINS_KEY_VALUE-}
    integer index=0

    # The scaffold-owned append is the last exact match. Do not insert or
    # reorder an indistinguishable equal entry after it before unloading.
    if (( added )) && [[ -n $functions_dir ]]; then
      index=${fpath[(Ie)$functions_dir]}
      (( index )) && fpath[index]=()
    fi

    if (( key_existed )); then
      Plugins[__KEY__]=$key_value
    else
      builtin unset 'Plugins[__KEY__]'
    fi

    builtin unset __FPATH_VAR__ __FPATH_VAR___ADDED
    builtin unset __FPATH_VAR___PLUGINS_KEY_EXISTED
    builtin unset __FPATH_VAR___PLUGINS_KEY_VALUE
    builtin unfunction __NAME___plugin_unload
  }
} "${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
