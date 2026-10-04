#!/usr/bin/env bash
set -euo pipefail

fail() {
  printf 'trunk-safe-ci: %s\n' "$*" >&2
  exit 2
}

: "${TRUNK_SAFE_WRAPPER:?TRUNK_SAFE_WRAPPER is required}"
: "${TRUNK_PATH:?TRUNK_PATH is required}"

mode=${TRUNK_SAFE_CHECK_MODE-}
event_name=${TRUNK_SAFE_EVENT_NAME-}
ref_name=${TRUNK_SAFE_REF_NAME-}
before=${TRUNK_SAFE_BEFORE-}
after=${TRUNK_SAFE_AFTER-}
pr_base_sha=${TRUNK_SAFE_PR_BASE_SHA-}
pr_head_sha=${TRUNK_SAFE_PR_HEAD_SHA-}
timeout_seconds=${TRUNK_SAFE_TIMEOUT_SECONDS:-0}

if [[ -z $mode ]]; then
  case $event_name in
  pull_request | pull_request_target) mode=pull_request ;;
  push) mode=push ;;
  schedule | workflow_dispatch) mode=all ;;
  *) mode=none ;;
  esac
fi

case $mode in
all | none | populate_cache_only | pull_request | push | trunk_merge) ;;
*) fail "unsupported check mode: $mode" ;;
esac

if [[ ${TRUNK_SAFE_DEBUG:-false} == true ]]; then
  printf 'Selected safe Trunk check mode: %s\n' "$mode"
fi

[[ $mode != none ]] || exit 0

args=(check --ci)
case $mode in
all | populate_cache_only)
  args+=(--all)
  [[ -z $after ]] || args+=(--github-commit "$after")
  ;;
pull_request)
  if [[ $ref_name == */merge ]]; then
    upstream=$(git rev-parse HEAD^1)
    commit=$(git rev-parse HEAD^2)
  else
    [[ -n $pr_base_sha ]] || fail "pull request base SHA is required"
    [[ -n $pr_head_sha ]] || fail "pull request head SHA is required"
    upstream=$pr_base_sha
    commit=$pr_head_sha
  fi
  args+=(--upstream "$upstream" --github-commit "$commit")
  ;;
push | trunk_merge)
  if [[ $ref_name == gh-readonly-queue/* || $mode == trunk_merge ]]; then
    upstream=$(git rev-parse HEAD^1)
  elif [[ -z $before || $before == 0000000000000000000000000000000000000000 ]]; then
    args+=(--all)
    upstream=
  else
    upstream=$before
  fi
  [[ -z $upstream ]] || args+=(--upstream "$upstream")
  [[ -z $after ]] || args+=(--github-commit "$after")
  ;;
esac

if [[ -n ${TRUNK_SAFE_ARGUMENTS-} ]]; then
  read -r -a extra_args <<<"$TRUNK_SAFE_ARGUMENTS"
  for arg in "${extra_args[@]}"; do
    case $arg in
    --token | --token=* | --github-token | --github-token=* | --trunk-token | --trunk-token=*)
      fail "credential-bearing Trunk arguments are not allowed"
      ;;
    esac
  done
  args+=("${extra_args[@]}")
fi

command=("$TRUNK_SAFE_WRAPPER" --trunk-path "$TRUNK_PATH" -- "${args[@]}")
if [[ $timeout_seconds == 0 ]]; then
  "${command[@]}"
else
  [[ $timeout_seconds =~ ^[0-9]+$ ]] || fail "timeout must be a non-negative integer"
  timeout --preserve-status "$timeout_seconds" "${command[@]}"
fi
