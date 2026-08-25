#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT=$ROOT/scripts/trunk-safe-ci.sh
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/trunk-safe-ci-test.XXXXXX")
trap 'rm -rf -- "$TEST_TMP"' EXIT HUP INT TERM

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local needle=$1
  local file=$2
  grep -Fxq -- "$needle" "$file" || fail "expected $file to contain an argument: $needle"
}

assert_not_contains() {
  local needle=$1
  local file=$2
  if grep -Fxq -- "$needle" "$file"; then
    fail "did not expect $file to contain an argument: $needle"
  fi
}

FAKE_WRAPPER=$TEST_TMP/fake-wrapper
cat >"$FAKE_WRAPPER" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" >"$CAPTURE_ARGS"
EOF
chmod +x "$FAKE_WRAPPER"

CAPTURE_ARGS=$TEST_TMP/arguments
export CAPTURE_ARGS

TRUNK_SAFE_WRAPPER=$FAKE_WRAPPER \
  TRUNK_PATH=/tmp/fake-trunk \
  TRUNK_SAFE_CHECK_MODE=all \
  TRUNK_SAFE_AFTER=after-sha \
  TRUNK_SAFE_ARGUMENTS='--no-progress --no-fix' \
  "$SCRIPT"

assert_contains "--trunk-path" "$CAPTURE_ARGS"
assert_contains "/tmp/fake-trunk" "$CAPTURE_ARGS"
assert_contains "check" "$CAPTURE_ARGS"
assert_contains "--ci" "$CAPTURE_ARGS"
assert_contains "--all" "$CAPTURE_ARGS"
assert_contains "--github-commit" "$CAPTURE_ARGS"
assert_contains "after-sha" "$CAPTURE_ARGS"
assert_contains "--no-progress" "$CAPTURE_ARGS"
assert_contains "--no-fix" "$CAPTURE_ARGS"

TRUNK_SAFE_WRAPPER=$FAKE_WRAPPER \
  TRUNK_PATH=/tmp/fake-trunk \
  TRUNK_SAFE_CHECK_MODE=pull_request \
  TRUNK_SAFE_REF_NAME=feature-branch \
  TRUNK_SAFE_PR_BASE_SHA=base-sha \
  TRUNK_SAFE_PR_HEAD_SHA=head-sha \
  "$SCRIPT"

assert_contains "--upstream" "$CAPTURE_ARGS"
assert_contains "base-sha" "$CAPTURE_ARGS"
assert_contains "head-sha" "$CAPTURE_ARGS"
assert_not_contains "--all" "$CAPTURE_ARGS"

rm -f "$CAPTURE_ARGS"
TRUNK_SAFE_WRAPPER=$FAKE_WRAPPER \
  TRUNK_PATH=/tmp/fake-trunk \
  TRUNK_SAFE_CHECK_MODE=none \
  "$SCRIPT"
[[ ! -e $CAPTURE_ARGS ]] || fail "none mode invoked the wrapper"

set +e
TRUNK_SAFE_WRAPPER=$FAKE_WRAPPER \
  TRUNK_PATH=/tmp/fake-trunk \
  TRUNK_SAFE_CHECK_MODE=unsupported \
  "$SCRIPT" >"$TEST_TMP/out" 2>"$TEST_TMP/err"
status=$?
set -e
[[ $status -eq 2 ]] || fail "expected invalid mode exit 2, got $status"

set +e
TRUNK_SAFE_WRAPPER=$FAKE_WRAPPER \
  TRUNK_PATH=/tmp/fake-trunk \
  TRUNK_SAFE_CHECK_MODE=all \
  TRUNK_SAFE_ARGUMENTS='--token=synthetic-secret' \
  "$SCRIPT" >"$TEST_TMP/out" 2>"$TEST_TMP/err"
status=$?
set -e
[[ $status -eq 2 ]] || fail "expected credential argument exit 2, got $status"
grep -Fq "credential-bearing Trunk arguments are not allowed" "$TEST_TMP/err" ||
  fail "credential argument rejection was not reported"

printf 'ok - CI check modes preserve Trunk scope\n'
printf 'ok - disabled and invalid modes are handled safely\n'
printf 'ok - credential-bearing arguments are rejected\n'
