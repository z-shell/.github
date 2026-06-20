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

# https://wiki.zshell.dev/community/zsh_plugin_standard#funtions-directory
typeset -g __FPATH_VAR__="${0:h}/functions"
if [[ $PMSPEC != *f* ]]; then
  fpath+=( "${__FPATH_VAR__}" )
fi

# --- Plugin body -------------------------------------------------------------
# Source library files or autoload functions here, e.g.:
#   source "${0:h}/lib/setup.zsh"
#   autoload -Uz +X .__NAME__ && .__NAME__

# https://wiki.zshell.dev/community/zsh_plugin_standard#unload-function
__NAME___plugin_unload() {
  # Remove our functions/ dir from fpath
  fpath=("${fpath[@]:#${__FPATH_VAR__}}")

  # TODO: unset variables, remove aliases, remove hooks, unfunction helpers,
  #       and restore any options/state this plugin changed.

  unset __FPATH_VAR__ 'Plugins[__KEY__]'

  unfunction __NAME___plugin_unload
}
