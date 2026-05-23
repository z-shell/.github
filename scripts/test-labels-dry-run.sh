#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT="$ROOT/scripts/labels-sync.rb"
COMPAT_SCRIPT="$ROOT/scripts/labels-dry-run.rb"
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
ruby -c "$COMPAT_SCRIPT" >/dev/null

# Existing refusal paths.
assert_exit 2 "$SCRIPT"
assert_exit 2 "$SCRIPT" --repo z-shell/.github --all-repos
assert_exit 2 "$SCRIPT" --repo

# New apply-mode guardrails.
assert_exit 2 "$SCRIPT" --repo z-shell/.github --confirm-apply
assert_exit 2 "$SCRIPT" --all-repos --apply
assert_exit 2 "$SCRIPT" --all-repos --apply --confirm-apply
assert_exit 2 "$SCRIPT" --repo z-shell/zi --apply --confirm-apply

# Backward-compatible dry-run entrypoint should keep working.
assert_json_field apply-preview "$COMPAT_SCRIPT" --repo z-shell/.github --apply --json

FAKE_BIN="$TEST_TMP/bin"
mkdir -p "$FAKE_BIN"
cat >"$FAKE_BIN/gh" <<'GH'
#!/usr/bin/env sh
set -eu
if [ "$1" = "api" ] && [ "$2" = "repos/z-shell/.github/labels?per_page=100" ]; then
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/z-shell/.github/labels" ] && [ "$3" = "--method" ] && [ "$4" = "POST" ]; then
  printf 'forced create failure\n' >&2
  exit 1
fi
printf 'unexpected gh call: %s\n' "$*" >&2
exit 1
GH
chmod +x "$FAKE_BIN/gh"

FAILING_LABELS="$TEST_TMP/labels.yml"
cat >"$FAILING_LABELS" <<'YAML'
labels:
  - name: test-label
    color: ff0000
    description: Test label
legacy_migrations: {}
sync_policy: {}
YAML

set +e
PATH="$FAKE_BIN:$PATH" "$SCRIPT" \
  --labels-file "$FAILING_LABELS" \
  --repo z-shell/.github \
  --apply \
  --confirm-apply \
  --include-clean >"$OUT" 2>"$ERR"
code=$?
set -e
[ "$code" = 1 ] || {
  cat "$OUT" >&2 || true
  cat "$ERR" >&2 || true
  fail "expected markdown apply failure to exit 1, got $code"
}
grep -q '^### Apply errors' "$OUT" || fail "expected markdown apply errors section"
grep -q '^- create test-label: .*forced create failure' "$OUT" || fail "expected formatted apply error in markdown"

printf 'labels-sync smoke tests passed\n'
