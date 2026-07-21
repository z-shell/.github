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

# Migrate and delete guardrails: confirm flags require their preview flag.
assert_exit 2 "$SCRIPT" --repo z-shell/.github --confirm-migrate-legacy
assert_exit 2 "$SCRIPT" --repo z-shell/.github --confirm-delete-unused-legacy

# Neither destructive mode may run against --all-repos.
assert_exit 2 "$SCRIPT" --all-repos --migrate-legacy
assert_exit 2 "$SCRIPT" --all-repos --delete-unused-legacy
assert_exit 2 "$SCRIPT" --all-repos --migrate-legacy --confirm-migrate-legacy
assert_exit 2 "$SCRIPT" --all-repos --delete-unused-legacy --confirm-delete-unused-legacy

# Confirmed destructive runs stay inside the pilot allowlist.
assert_exit 2 "$SCRIPT" --repo z-shell/zi --migrate-legacy --confirm-migrate-legacy
assert_exit 2 "$SCRIPT" --repo z-shell/zi --delete-unused-legacy --confirm-delete-unused-legacy

# Preview modes are read-only and must report their own mode.
assert_json_field migrate-preview "$SCRIPT" --repo z-shell/.github --migrate-legacy --json
assert_json_field delete-preview "$SCRIPT" --repo z-shell/.github --delete-unused-legacy --json

# sync_policy is the source of truth: a policy that forbids the operation refuses
# it even when every flag is supplied correctly.
POLICY_OFF="$TEST_TMP/policy-off.yml"
cat >"$POLICY_OFF" <<'YAML'
labels:
  - name: type:bug
    color: ff0000
    description: Bug
legacy_migrations:
  "bug 🐞": type:bug
sync_policy:
  delete_unknown_labels: false
  delete_legacy_labels_only_when_unused: false
  preserve_labels_on_open_items_before_removal: true
YAML
assert_exit 2 "$SCRIPT" --labels-file "$POLICY_OFF" --repo z-shell/.github \
  --delete-unused-legacy --confirm-delete-unused-legacy

# A legacy label that is still in use must never be deleted directly. The fake gh
# reports one carrying item, so the delete path has to refuse it.
INUSE_BIN="$TEST_TMP/inuse-bin"
DELETE_MARKER="$TEST_TMP/delete-attempted"
export DELETE_MARKER
mkdir -p "$INUSE_BIN"
cat >"$INUSE_BIN/gh" <<'GH'
#!/usr/bin/env sh
set -eu
case "$*" in
  *"/labels?per_page=100"*)
    printf '{"name":"bug 🐞","color":"d73a4a","description":"legacy"}\n'
    exit 0
    ;;
  *"issues?state=all"*)
    printf '{"number":7,"labels":[{"name":"bug 🐞"}]}\n'
    exit 0
    ;;
  *--method\ DELETE*)
    # Record out-of-band: the script captures our stderr, so a message there
    # would never reach the test.
    printf 'delete attempted\n' >>"$DELETE_MARKER"
    exit 90
    ;;
esac
printf '\n'
exit 0
GH
chmod +x "$INUSE_BIN/gh"

INUSE_LABELS="$TEST_TMP/inuse.yml"
cat >"$INUSE_LABELS" <<'YAML'
labels:
  - name: type:bug
    color: d73a4a
    description: Bug
legacy_migrations:
  "bug 🐞": type:bug
sync_policy:
  delete_unknown_labels: false
  delete_legacy_labels_only_when_unused: true
  preserve_labels_on_open_items_before_removal: true
YAML

set +e
PATH="$INUSE_BIN:$PATH" "$SCRIPT" \
  --labels-file "$INUSE_LABELS" \
  --repo z-shell/.github \
  --delete-unused-legacy \
  --confirm-delete-unused-legacy \
  --json >"$OUT" 2>"$ERR"
code=$?
set -e

# The guard: an in-use legacy label must never reach the delete path.
if [ -e "$DELETE_MARKER" ]; then
  fail "delete path issued DELETE for an in-use legacy label"
fi

# ...and it must be routed to migration instead, with nothing queued for deletion.
ruby -rjson -e '
  data = JSON.parse(File.read(ARGV.fetch(0)))
  ops = data.fetch("results").fetch(0).fetch("legacy_operations")
  unless ops.fetch("would_delete_unused").empty?
    abort "in-use legacy label was queued for deletion: #{ops.fetch('"'"'would_delete_unused'"'"').inspect}"
  end
  migrating = ops.fetch("would_migrate").map { |m| m.fetch("legacy") }
  unless migrating.include?("bug 🐞")
    abort "in-use legacy label was not queued for migration: #{migrating.inspect}"
  end
' "$OUT" || fail "in-use legacy label was not handled correctly"

[ "$code" = 0 ] || fail "expected clean exit for in-use legacy preview, got $code"

# Migration order is load-bearing: the canonical label must be added to every
# carrying item BEFORE the legacy label is deleted. Deleting first would strip
# the association with nothing to replace it. This stub logs call order.
ORDER_BIN="$TEST_TMP/order-bin"
ORDER_LOG="$TEST_TMP/order.log"
export ORDER_LOG
mkdir -p "$ORDER_BIN"
: >"$ORDER_LOG"
cat >"$ORDER_BIN/gh" <<'GH'
#!/usr/bin/env sh
set -eu
case "$*" in
  *"/labels?per_page=100"*)
    printf '{"name":"bug 🐞","color":"d73a4a","description":"legacy"}\n'
    exit 0
    ;;
  *"issues?state=all"*)
    # After the relabel has been recorded, report the canonical label as present
    # so the script's own verification step can succeed.
    if grep -q '^ADD' "$ORDER_LOG" 2>/dev/null; then
      printf '{"number":7,"labels":[{"name":"bug 🐞"},{"name":"type:bug"}]}\n'
    else
      printf '{"number":7,"labels":[{"name":"bug 🐞"}]}\n'
    fi
    exit 0
    ;;
  *"/issues/7/labels"*--method\ POST*)
    printf 'ADD\n' >>"$ORDER_LOG"
    printf '\n'
    exit 0
    ;;
  *--method\ DELETE*)
    printf 'DELETE\n' >>"$ORDER_LOG"
    printf '\n'
    exit 0
    ;;
esac
printf '\n'
exit 0
GH
chmod +x "$ORDER_BIN/gh"

assert_success env PATH="$ORDER_BIN:$PATH" "$SCRIPT" \
  --labels-file "$INUSE_LABELS" \
  --repo z-shell/.github \
  --migrate-legacy \
  --confirm-migrate-legacy \
  --json

grep -q '^ADD' "$ORDER_LOG" || fail "migration never added the canonical label"
grep -q '^DELETE' "$ORDER_LOG" || fail "migration never removed the legacy label"
[ "$(head -n 1 "$ORDER_LOG")" = "ADD" ] || {
  cat "$ORDER_LOG" >&2
  fail "migration deleted the legacy label before relabelling items"
}

# Preview modes must be read-only: no POST, no DELETE, for either mode.
: >"$ORDER_LOG"
assert_success env PATH="$ORDER_BIN:$PATH" "$SCRIPT" \
  --labels-file "$INUSE_LABELS" --repo z-shell/.github --migrate-legacy --json
[ -s "$ORDER_LOG" ] && {
  cat "$ORDER_LOG" >&2
  fail "--migrate-legacy preview issued write calls"
}

: >"$ORDER_LOG"
assert_success env PATH="$ORDER_BIN:$PATH" "$SCRIPT" \
  --labels-file "$INUSE_LABELS" --repo z-shell/.github --delete-unused-legacy --json
[ -s "$ORDER_LOG" ] && {
  cat "$ORDER_LOG" >&2
  fail "--delete-unused-legacy preview issued write calls"
}

# An item that acquires the legacy label between planning and deletion must not
# lose it. Deleting a label strips it from every holder at that moment, so the
# migration has to re-check for late arrivals before it deletes.
RACE_BIN="$TEST_TMP/race-bin"
RACE_LOG="$TEST_TMP/race.log"
export RACE_LOG
mkdir -p "$RACE_BIN"
: >"$RACE_LOG"
cat >"$RACE_BIN/gh" <<'GH'
#!/usr/bin/env sh
set -eu
case "$*" in
  *"/labels?per_page=100"*)
    printf '{"name":"bug 🐞","color":"d73a4a","description":"legacy"}\n'
    exit 0
    ;;
  *"issues?state=all"*)
    # Item 7 is known at plan time. Item 8 shows up carrying the legacy label
    # only after the first relabel — the race this guards against.
    if grep -q '^ADD 7' "$RACE_LOG" 2>/dev/null; then
      printf '{"number":7,"labels":[{"name":"bug 🐞"},{"name":"type:bug"}]}\n'
      if grep -q '^ADD 8' "$RACE_LOG" 2>/dev/null; then
        printf '{"number":8,"labels":[{"name":"bug 🐞"},{"name":"type:bug"}]}\n'
      else
        printf '{"number":8,"labels":[{"name":"bug 🐞"}]}\n'
      fi
    else
      printf '{"number":7,"labels":[{"name":"bug 🐞"}]}\n'
    fi
    exit 0
    ;;
  *"/issues/7/labels"*--method\ POST*) printf 'ADD 7\n' >>"$RACE_LOG"; printf '\n'; exit 0 ;;
  *"/issues/8/labels"*--method\ POST*) printf 'ADD 8\n' >>"$RACE_LOG"; printf '\n'; exit 0 ;;
  *--method\ DELETE*) printf 'DELETE\n' >>"$RACE_LOG"; printf '\n'; exit 0 ;;
esac
printf '\n'
exit 0
GH
chmod +x "$RACE_BIN/gh"

assert_success env PATH="$RACE_BIN:$PATH" "$SCRIPT" \
  --labels-file "$INUSE_LABELS" \
  --repo z-shell/.github \
  --migrate-legacy \
  --confirm-migrate-legacy \
  --json

grep -q '^ADD 8' "$RACE_LOG" || {
  cat "$RACE_LOG" >&2
  fail "late-arriving item 8 never received the canonical label"
}
[ "$(grep -n '^DELETE' "$RACE_LOG" | head -n 1 | cut -d: -f1)" -gt \
  "$(grep -n '^ADD 8' "$RACE_LOG" | head -n 1 | cut -d: -f1)" ] || {
  cat "$RACE_LOG" >&2
  fail "legacy label was deleted before the late-arriving item was relabelled"
}

printf 'labels-sync smoke tests passed\n'
