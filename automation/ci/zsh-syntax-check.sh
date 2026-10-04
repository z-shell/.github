#!/usr/bin/env bash
# PostToolUse hook: run `zsh -n` on edited Zsh files.
# Reads the hook JSON payload from stdin, extracts the edited file path,
# and reports a syntax error back to Claude (exit 2) if `zsh -n` fails.
set -euo pipefail

payload="$(cat)"

file_path="$(printf '%s' "$payload" | jq -r '.tool_input.file_path // .tool_input.path // empty')"
[ -n "$file_path" ] || exit 0

case "$file_path" in
  *.zsh | *.plugin.zsh | *.zsh-theme | *zshrc | *zshenv) ;;
  *) exit 0 ;;
esac

[ -f "$file_path" ] || exit 0
command -v zsh >/dev/null 2>&1 || exit 0

if ! err="$(zsh -n "$file_path" 2>&1)"; then
  printf 'zsh -n found a syntax error in %s:\n%s\n' "$file_path" "$err" >&2
  exit 2
fi

exit 0
