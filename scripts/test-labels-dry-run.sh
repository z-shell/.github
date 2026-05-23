#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT="$ROOT/scripts/labels-dry-run.rb"
TMPDIR=${TMPDIR:-/tmp}
TEST_TMP=$(mktemp -d "$TMPDIR/labels-dry-run-test.XXXXXX")
OUT="$TEST_TMP/out"
ERR="$TEST_TMP/err"
trap 'rm -rf "$TEST_TMP"' EXIT HUP INT TERM

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_success() {
  "$@" >"$OUT" 2>"$ERR" || {
    cat "$ERR" >&2
    fail "expected success: $*"
  }
}

assert_exit() {
  expected=$1
  shift
  set +e
  "$@" >"$OUT" 2>"$ERR"
  code=$?
  set -e
  [ "$code" = "$expected" ] || {
    cat "$OUT" >&2 || true
    cat "$ERR" >&2 || true
    fail "expected exit $expected, got $code: $*"
  }
}

assert_json_field() {
  expected=$1
  shift
  "$@" | ruby -rjson -e "data=JSON.parse(STDIN.read); actual=data.fetch('mode'); abort %(expected mode #{ARGV.fetch(0)}, got #{actual}) unless actual == ARGV.fetch(0)" "$expected"
}

ruby -c "$SCRIPT" >/dev/null

# Existing refusal paths.
assert_exit 2 "$SCRIPT"
assert_exit 2 "$SCRIPT" --repo z-shell/.github --all-repos
assert_exit 2 "$SCRIPT" --repo

# New apply-mode guardrails.
assert_exit 2 "$SCRIPT" --repo z-shell/.github --confirm-apply
assert_exit 2 "$SCRIPT" --all-repos --apply
assert_exit 2 "$SCRIPT" --all-repos --apply --confirm-apply
assert_exit 2 "$SCRIPT" --repo z-shell/zi --apply --confirm-apply

# Apply preview must be machine-readable and non-mutating.
assert_json_field apply-preview "$SCRIPT" --repo z-shell/.github --apply --json

printf 'labels-dry-run smoke tests passed\n'
