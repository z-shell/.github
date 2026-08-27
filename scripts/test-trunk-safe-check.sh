#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT=$ROOT/scripts/trunk-safe-check.sh
TMPDIR=${TMPDIR:-/tmp}
TEST_TMP=$(mktemp -d "$TMPDIR/trunk-safe-check-test.XXXXXX")
trap 'rm -rf -- "$TEST_TMP"' EXIT HUP INT TERM

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  needle=$1
  file=$2
  grep -Fq -- "$needle" "$file" || fail "expected $file to contain: $needle"
}

assert_not_contains() {
  needle=$1
  file=$2
  if grep -Fq -- "$needle" "$file"; then
    fail "did not expect $file to contain: $needle"
  fi
}

assert_runtime_clean() {
  for entry in "$TEST_TMP/runtime"/z-shell-trunk.*; do
    [ ! -e "$entry" ] || fail "wrapper left a runtime directory behind"
  done
}

FAKE_TRUNK=$TEST_TMP/fake-trunk
cat >"$FAKE_TRUNK" <<'EOF'
#!/usr/bin/env sh
set -eu

capture_env=
capture_args=
exit_status=0
internal_failure=false

while [ "$#" -gt 0 ]; do
  case $1 in
    --capture-env)
      capture_env=$2
      shift 2
      ;;
    --capture-args)
      capture_args=$2
      shift 2
      ;;
    --exit)
      exit_status=$2
      shift 2
      ;;
    --internal-failure)
      internal_failure=true
      shift
      ;;
    *)
      [ -n "$capture_args" ] && printf '%s\n' "$1" >>"$capture_args"
      shift
      ;;
  esac
done

[ -z "$capture_env" ] || env | LC_ALL=C sort >"$capture_env"
if [ "$internal_failure" = true ]; then
  printf 'failed tool execution\n' >&2
  printf 'RAW_DIAGNOSTIC_MARKER\n' >&2
else
  printf 'fake trunk completed\n'
fi
exit "$exit_status"
EOF
chmod +x "$FAKE_TRUNK"

mkdir -p "$TEST_TMP/runtime"
OUT=$TEST_TMP/out
ERR=$TEST_TMP/err
CAPTURED_ENV=$TEST_TMP/environment
CAPTURED_ARGS=$TEST_TMP/arguments
SENTINEL_VALUE=sentinel-must-not-reach-trunk

CI=caller-controlled-value LEAK_SENTINEL=$SENTINEL_VALUE TMPDIR=$TEST_TMP/runtime \
  "$SCRIPT" --trunk-path "$FAKE_TRUNK" -- \
  --capture-env "$CAPTURED_ENV" \
  --capture-args "$CAPTURED_ARGS" \
  check "path with spaces" >"$OUT" 2>"$ERR"

assert_contains "fake trunk completed" "$OUT"
assert_not_contains "$SENTINEL_VALUE" "$CAPTURED_ENV"
assert_not_contains "LEAK_SENTINEL=" "$CAPTURED_ENV"
assert_contains "CI=true" "$CAPTURED_ENV"
assert_not_contains "caller-controlled-value" "$CAPTURED_ENV"
assert_contains "HOME=$TEST_TMP/runtime/z-shell-trunk." "$CAPTURED_ENV"
assert_contains "TRUNK_CACHE=$TEST_TMP/runtime/z-shell-trunk." "$CAPTURED_ENV"
assert_contains "check" "$CAPTURED_ARGS"
assert_contains "path with spaces" "$CAPTURED_ARGS"

assert_runtime_clean

set +e
TMPDIR=$TEST_TMP/runtime "$SCRIPT" --trunk-path "$FAKE_TRUNK" -- \
  --exit 17 >"$OUT" 2>"$ERR"
status=$?
set -e
[ "$status" -eq 17 ] || fail "expected exit 17, got $status"

set +e
TMPDIR=$TEST_TMP/runtime "$SCRIPT" --trunk-path "$FAKE_TRUNK" -- \
  --internal-failure --exit 23 >"$OUT" 2>"$ERR"
status=$?
set -e
[ "$status" -eq 23 ] || fail "expected exit 23, got $status"
assert_contains "verbose diagnostics were suppressed" "$ERR"
assert_not_contains "RAW_DIAGNOSTIC_MARKER" "$OUT"
assert_not_contains "RAW_DIAGNOSTIC_MARKER" "$ERR"

assert_runtime_clean

printf 'ok - Trunk environment is isolated\n'
printf 'ok - Trunk arguments and exit status are preserved\n'
printf 'ok - internal failure diagnostics are suppressed\n'
