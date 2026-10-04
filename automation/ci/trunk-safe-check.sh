#!/usr/bin/env sh
set -eu

usage() {
  cat <<'EOF'
Usage: automation/ci/trunk-safe-check.sh [--trunk-path PATH] -- ARG...

Run Trunk with a minimal environment and disposable runtime directories.
The arguments after -- are passed to Trunk unchanged.
EOF
}

fail() {
  printf 'trunk-safe-check: %s\n' "$*" >&2
  exit 2
}

trunk_path=
while [ "$#" -gt 0 ]; do
  case $1 in
  --trunk-path)
    [ "$#" -ge 2 ] || fail "--trunk-path requires a value"
    trunk_path=$2
    shift 2
    ;;
  --help | -h)
    usage
    exit 0
    ;;
  --)
    shift
    break
    ;;
  *)
    fail "unknown option: $1"
    ;;
  esac
done

[ "$#" -gt 0 ] || fail "missing Trunk arguments after --"

if [ -z "$trunk_path" ]; then
  trunk_path=$(command -v trunk 2>/dev/null || true)
fi
[ -n "$trunk_path" ] || fail "trunk executable not found"
[ -x "$trunk_path" ] || fail "trunk executable is not executable: $trunk_path"

case $trunk_path in
/*) ;;
*) trunk_path=$(CDPATH='' cd -- "$(dirname -- "$trunk_path")" && pwd)/$(basename -- "$trunk_path") ;;
esac

runtime_parent=${TMPDIR:-/tmp}
[ -d "$runtime_parent" ] || fail "temporary directory does not exist: $runtime_parent"

umask 077
runtime_dir=$(mktemp -d "$runtime_parent/z-shell-trunk.XXXXXX")
# Invoked through the signal and exit trap below.
# shellcheck disable=SC2329
cleanup() {
  # `trunk check` leaves a daemon and its crash handler running. Stop them with
  # the same isolated environment while the runtime directory still exists. A
  # signal runs this trap and exit runs it again, so shut down only once.
  if [ -n "${trunk_ran-}" ]; then
    trunk_ran=
    run_trunk daemon shutdown >/dev/null 2>&1 || true
  fi
  rm -rf -- "$runtime_dir"
}
# Invoked through the signal traps below.
# shellcheck disable=SC2329
on_signal() {
  # Clean up once and stop, so the script does not carry on without its
  # runtime directory; exit with the conventional 128 + signal number.
  trap - EXIT HUP INT TERM
  cleanup
  exit "$1"
}
trap cleanup EXIT
trap 'on_signal 129' HUP
trap 'on_signal 130' INT
trap 'on_signal 143' TERM

mkdir -p \
  "$runtime_dir/cache" \
  "$runtime_dir/config" \
  "$runtime_dir/data" \
  "$runtime_dir/home" \
  "$runtime_dir/tmp"

stdout_file=$runtime_dir/stdout
stderr_file=$runtime_dir/stderr
ci_value=
[ -z "${CI-}" ] || ci_value=true

run_trunk() {
  env -i \
    CI="$ci_value" \
    HOME="$runtime_dir/home" \
    LANG=C \
    LC_ALL=C \
    NO_COLOR=1 \
    PATH="${PATH:-/usr/bin:/bin}" \
    TERM=dumb \
    TMPDIR="$runtime_dir/tmp" \
    TRUNK_CACHE="$runtime_dir/cache" \
    TRUNK_LAUNCHER_QUIET=false \
    XDG_CACHE_HOME="$runtime_dir/cache" \
    XDG_CONFIG_HOME="$runtime_dir/config" \
    XDG_DATA_HOME="$runtime_dir/data" \
    "$trunk_path" "$@"
}

set +e
trunk_ran=1
run_trunk "$@" >"$stdout_file" 2>"$stderr_file"
status=$?
set -e

if [ "$status" -ne 0 ] &&
  grep -Eiq 'failed tool execution|failure\.ya?ml|internal (error|failure)' "$stdout_file" "$stderr_file"; then
  printf 'Trunk failed internally with status %s; verbose diagnostics were suppressed.\n' "$status" >&2
else
  cat "$stdout_file"
  cat "$stderr_file" >&2
fi

exit "$status"
