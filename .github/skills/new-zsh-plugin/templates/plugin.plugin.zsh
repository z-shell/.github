# -*- mode: zsh; sh-indentation: 2; indent-tabs-mode: nil; sh-basic-offset: 2; -*-
# vim: ft=zsh sw=2 ts=2 et
#
# Zsh Plugin Standard
# https://wiki.zshell.dev/community/zsh_plugin_standard#zero-handling
0="${ZERO:-${${0:#$ZSH_ARGZERO}:-${(%):-%N}}}"
0="${${(M)0:#/*}:-$PWD/$0}"

# https://wiki.zshell.dev/community/zsh_plugin_standard#standard-plugins-hash
typeset -gA Plugins
Plugins[__KEY__]="${0:h}"

# https://wiki.zshell.dev/community/zsh_plugin_standard#functions-directory
# Canonical rule: zsh/security/trust-paths
typeset -g __FPATH_VAR__="${0:h}/functions"
typeset -gi __FPATH_VAR___ADDED=0
if [[ ${PMSPEC-} != *f* ]] &&
  (( ${fpath[(Ie)${__FPATH_VAR__}]} == 0 )); then
  fpath+=( "${__FPATH_VAR__}" )
  __FPATH_VAR___ADDED=1
fi

# --- Plugin body -------------------------------------------------------------
# Source library files or autoload functions here, e.g.:
#   source "${0:h}/lib/setup.zsh"
#   autoload -Uz +X .__NAME__ && .__NAME__
# Pair every added side effect with its exact cleanup in the unload function.

# https://wiki.zshell.dev/community/zsh_plugin_standard#unload-function
# Canonical rule: zsh/plugin/restore-state
__NAME___plugin_unload() {
  if (( ${__FPATH_VAR___ADDED:-0} )) &&
    (( ${fpath[(Ie)${__FPATH_VAR__}]} != 0 )); then
    fpath[${fpath[(ie)${__FPATH_VAR__}]}]=()
  fi

  unset __FPATH_VAR__ __FPATH_VAR___ADDED 'Plugins[__KEY__]'

  unfunction __NAME___plugin_unload
}
