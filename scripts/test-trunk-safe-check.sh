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

# Every call is recorded next to this script, since the wrapper clears the
# environment: one line of arguments and the HOME it ran with.
fake_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
printf '%s | HOME=%s\n' "$*" "${HOME-}" >>"$fake_dir/invocations"

if [ "${1-}" = daemon ] && [ "${2-}" = shutdown ]; then
  # The daemon's state lives under HOME; a shutdown after the wrapper removed it
  # would reach no daemon.
  [ -d "${HOME-}" ] || printf 'HOME_MISSING_AT_SHUTDOWN\n' >>"$fake_dir/invocations"
  if [ -e "$fake_dir/fail-shutdown" ]; then
    printf 'SHUTDOWN_NOISE\n'
    printf 'SHUTDOWN_NOISE\n' >&2
    exit 9
  fi
  exit 0
fi

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

# The wrapper asks Trunk to stop the daemon a check starts, in the same isolated
# environment and before the runtime directory is removed, on every exit path.
INVOCATIONS=$TEST_TMP/invocations
assert_shutdown_after_run() {
  label=$1
  [ "$(wc -l <"$INVOCATIONS")" -eq 2 ] || fail "$label: expected a run and one shutdown, got: $(cat "$INVOCATIONS")"
  last=$(tail -n 1 "$INVOCATIONS")
  case $last in
  "daemon shutdown | HOME=$TEST_TMP/runtime/z-shell-trunk."*/home) ;;
  *) fail "$label: last Trunk call was not an isolated daemon shutdown: $last" ;;
  esac
}

for case_args in "check" "--exit 17" "--internal-failure --exit 23"; do
  rm -f "$INVOCATIONS"
  set +e
  # shellcheck disable=SC2086 # the case arguments are split on purpose
  TMPDIR=$TEST_TMP/runtime "$SCRIPT" --trunk-path "$FAKE_TRUNK" -- $case_args >"$OUT" 2>"$ERR"
  set -e
  assert_shutdown_after_run "$case_args"
done
assert_runtime_clean

# A failing shutdown changes neither the exit status nor the output.
touch "$TEST_TMP/fail-shutdown"
set +e
TMPDIR=$TEST_TMP/runtime "$SCRIPT" --trunk-path "$FAKE_TRUNK" -- \
  --exit 17 >"$OUT" 2>"$ERR"
status=$?
set -e
rm -f "$TEST_TMP/fail-shutdown"
[ "$status" -eq 17 ] || fail "expected exit 17 when shutdown fails, got $status"
assert_not_contains "SHUTDOWN_NOISE" "$OUT"
assert_not_contains "SHUTDOWN_NOISE" "$ERR"
assert_runtime_clean

# An argument error exits before Trunk runs, so there is no daemon to stop.
rm -f "$INVOCATIONS"
set +e
TMPDIR=$TEST_TMP/runtime "$SCRIPT" --trunk-path "$FAKE_TRUNK" >"$OUT" 2>"$ERR"
status=$?
set -e
[ "$status" -eq 2 ] || fail "expected exit 2 without Trunk arguments, got $status"
[ ! -e "$INVOCATIONS" ] || fail "Trunk ran although the arguments were rejected: $(cat "$INVOCATIONS")"

printf 'ok - Trunk environment is isolated\n'
printf 'ok - Trunk arguments and exit status are preserved\n'
printf 'ok - internal failure diagnostics are suppressed\n'
printf 'ok - the Trunk daemon is shut down on every exit path\n'
