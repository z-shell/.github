# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Zsh Plugin Standard portable path handling
# https://wiki.zshell.dev/community/zsh_plugin_standard#zero-handling
0="${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
0="${${(M)0:#/*}:-$PWD/$0}"

# Optional manager capability: PMSPEC=f means the manager owns fpath setup.
# https://wiki.zshell.dev/community/zsh_plugin_standard#functions-directory
typeset -g __FPATH_VAR__="${0:h}/functions"
typeset -gi __FPATH_VAR___ADDED=${__FPATH_VAR___ADDED:-0}
if [[ ${PMSPEC-} != *f* ]] && (( ! ${fpath[(Ie)${__FPATH_VAR__}]} )); then
  fpath+=( "${__FPATH_VAR__}" )
  __FPATH_VAR___ADDED=1
fi

# --- Plugin body -------------------------------------------------------------
# Source library files or autoload functions here, e.g.:
#   source "${0:h}/lib/setup.zsh"
#   autoload -Uz +X .__NAME__ && .__NAME__

# https://wiki.zshell.dev/community/zsh_plugin_standard#unload-function
__NAME___plugin_unload() {
  local fpath_index
  if (( __FPATH_VAR___ADDED )); then
    fpath_index=${fpath[(Ie)${__FPATH_VAR__}]}
    (( fpath_index )) && fpath[$fpath_index]=()
  fi

  # TODO: unset variables, remove aliases, remove hooks, unfunction helpers,
  #       and restore any options/state this plugin changed.

  unset __FPATH_VAR__ __FPATH_VAR___ADDED

  unfunction __NAME___plugin_unload
}
