#!/usr/bin/env bash
# Tests the policy patterns in .github/workflows/commit-lint.yml.
#
# Every pattern is EXTRACTED from the workflow rather than restated here. A
# test carrying its own copy of a regex drifts from the thing it claims to
# check and then proves nothing, which is the second source of truth AGENTS.md
# warns against. If an extraction fails, that is a test failure: the workflow
# changed shape and this file has to be re-pointed, not quietly skipped.
#
# Three defects have shipped in that workflow (z-shell/.github#575, the empty
# pattern trap found in #586, and the fail-open in #587). Two of the three
# failed silently. The cases below exist so a fourth does not.
#
# Dialect: Bash, floor 4.0. CI runs it on ubuntu-latest, which ships Bash 5.
# ShellCheck applies with bash selected, per
# .github/instructions/shell.instructions.md.
set -euo pipefail

ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
WORKFLOW=$ROOT/.github/workflows/commit-lint.yml

failures=0
checks=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  failures=$((failures + 1))
}

# Pull the single capture of an anchored extraction, failing loudly when the
# workflow no longer has the shape this file assumes.
#
# Prettier owns YAML formatting here and rewrites scalar quoting at will, so
# every extraction strips one matching pair of surrounding quotes rather than
# depending on which style it last chose. Patterns inside a run: block scalar
# are untouched by prettier, but the same handling costs nothing.
extract() {
  local label=$1 regex=$2 value
  value=$(sed -nE "s/$regex/\1/p" "$WORKFLOW")
  case $value in
    \'*\') value=${value#\'}; value=${value%\'} ;;
    '"'*'"') value=${value#'"'}; value=${value%'"'} ;;
  esac
  if [ -z "$value" ]; then
    printf 'FAIL: could not extract %s from %s\n' "$label" "$WORKFLOW" >&2
    printf '      the workflow changed shape; re-point this test\n' >&2
    exit 1
  fi
  if [ "$(printf '%s\n' "$value" | wc -l)" -ne 1 ]; then
    printf 'FAIL: %s matched more than once in %s\n' "$label" "$WORKFLOW" >&2
    exit 1
  fi
  printf '%s' "$value"
}

TRAILER_PATTERN=$(extract "trailer pattern" \
  '^ *: "\$\{DISALLOWED_TRAILER_PATTERN:=(.*)\}"$')
BRANCH_PATTERN=$(extract "branch pattern" \
  '^ *: "\$\{BRANCH_PATTERN:=(.*)\}"$')
CONVENTIONAL_PATTERN=$(extract "conventional pattern" \
  "^ *CONVENTIONAL_PATTERN=(.*)$")
PREFIX_PATTERN=$(extract "automation prefixes" \
  "^ *AUTOMATION_BRANCH_PATTERN: (.*)$")
ISSUE_REFERENCE_PATTERN=$(extract "issue reference pattern" \
  "^ *ISSUE_REFERENCE_PATTERN=(.*)$")
EXEMPT_LABEL=$(extract "exemption label" \
  '^ *EXEMPT_LABEL: (.*)$')

# --- guards on the constructs themselves ---------------------------------

# z-shell/.github#587: grep -q exits on its first match, so under pipefail a
# commit message larger than the pipe buffer gives git a SIGPIPE and the
# pipeline reports no match. grep -c reads to the end and cannot fail open.
check_no_grep_q_on_trailer() {
  checks=$((checks + 1))
  if grep -q 'git show .*|[[:space:]]*grep -q' "$WORKFLOW"; then
    fail "trailer check pipes git show into grep -q; it fails open on a large message (#587)"
  fi
}

# z-shell/.github#586: workflow_call input defaults do not apply on a
# pull_request run, so each pattern needs an in-step fallback. An empty
# grep -E pattern matches every line, which silently passes every branch and
# flags every commit.
check_fallbacks_present() {
  local name
  for name in DISALLOWED_TRAILER_PATTERN BRANCH_PATTERN; do
    checks=$((checks + 1))
    grep -q ": \"\${$name:=" "$WORKFLOW" ||
      fail "$name has no in-step fallback; an empty pattern matches everything (#586)"
  done
}

# The same trap in the other direction: a default left on the workflow_call
# input is a second source of truth that the pull_request path never reads.
check_no_input_defaults() {
  checks=$((checks + 1))
  if sed -n '/workflow_call:/,/^concurrency:/p' "$WORKFLOW" | grep -q '^ *default:'; then
    fail "workflow_call input carries a default that a pull_request run ignores (#586)"
  fi
}

# decisions/0022: the exemption label the workflow honours has to be a label
# the organization actually publishes, or applying it is impossible.
check_exempt_label_is_canonical() {
  checks=$((checks + 1))
  grep -q "^  - name: $EXEMPT_LABEL\$" "$ROOT/lib/labels.yml" ||
    fail "exemption label '$EXEMPT_LABEL' is not declared in lib/labels.yml (ADR-0022)"
}

# Both jobs must read one definition of the automation prefixes. A second
# inlined copy is how the two silently diverge.
check_prefixes_not_duplicated() {
  checks=$((checks + 1))
  if grep -qE "grep -qE '\\^\\(dependabot" "$WORKFLOW"; then
    fail "automation prefixes are inlined as well as defined in env; the two copies will drift"
  fi
}

# --- table-driven pattern cases ------------------------------------------

# assert_match <label> <pattern> <subject> <expect: match|no-match>
assert_match() {
  local label=$1 pattern=$2 subject=$3 expect=$4 got
  checks=$((checks + 1))
  if printf '%s\n' "$subject" | grep -qE "$pattern"; then got=match; else got=no-match; fi
  [ "$got" = "$expect" ] ||
    fail "$label: expected $expect for '$subject', got $got"
}

# A branch is allowed when it carries an automation prefix, is zi's next, or
# matches the pattern. Mirrors the job's own order.
assert_branch() {
  local branch=$1 expect=$2 got
  checks=$((checks + 1))
  if printf '%s\n' "$branch" | grep -qE "$PREFIX_PATTERN" || [ "$branch" = next ]; then
    got=allow
  elif printf '%s\n' "$branch" | grep -qE "$BRANCH_PATTERN"; then
    got=allow
  else
    got=reject
  fi
  [ "$got" = "$expect" ] || fail "branch '$branch': expected $expect, got $got"
}

check_branch_cases() {
  assert_branch feature-1 allow
  assert_branch bug-592 allow
  assert_branch hotfix-42 allow
  assert_branch feature-478-repo-settings-audit allow
  assert_branch dependabot/npm_and_yarn/lodash-4.17.21 allow
  assert_branch renovate/actions-checkout allow
  assert_branch copilot/fix-metrics-job-failure allow
  assert_branch codex/learning-capture-publication allow
  assert_branch next allow

  # decisions/0022 relaxed this to a shape check, so a Conventional Commits
  # type prefix now passes without an identifier.
  assert_branch fix/labeler-audit-reject-malformed allow
  assert_branch docs/adr-0022-rollout allow
  assert_branch chore/tidy-workflows allow
  assert_branch feature/no-identifier allow

  # 'code' is not in the decisions/0003 type set, so it is still rejected.
  assert_branch code/promotion-precondition-ancestry reject
  assert_branch ss-o-govern-plugin-standard reject
  assert_branch fix/Bad-Caps reject
  assert_branch fix/ reject
  assert_branch feature-0 reject
  assert_branch feature- reject
  assert_branch feature-505- reject
  assert_branch feature-505-Bad-Caps reject
  assert_branch bugfix-12 reject
  assert_branch '' reject
}

check_trailer_cases() {
  local p=$TRAILER_PATTERN
  assert_match trailer "$p" 'Co-authored-by: dependabot[bot] <x@y>' match
  assert_match trailer "$p" 'Co-authored-by: Claude <noreply@anthropic.com>' match
  assert_match trailer "$p" 'Co-authored-by: Codex <codex@openai.com>' match
  assert_match trailer "$p" 'Co-authored-by: Copilot <copilot@github.com>' match
  assert_match trailer "$p" '  Co-authored-by: renovate[bot] <x@y>' match

  # A human co-author is explicitly allowed; only bot and agent identities are
  # banned. Getting this wrong bans legitimate credit.
  assert_match trailer "$p" 'Co-authored-by: Jane Doe <jane@example.com>' no-match
  assert_match trailer "$p" 'fix(ci): an ordinary subject' no-match
  assert_match trailer "$p" 'Signed-off-by: dependabot[bot] <x@y>' no-match
}

check_conventional_cases() {
  local p=$CONVENTIONAL_PATTERN
  assert_match subject "$p" 'fix(ci): stop the guard failing open' match
  assert_match subject "$p" 'chore: bump' match
  assert_match subject "$p" 'feat(api)!: drop the legacy field' match

  assert_match subject "$p" 'Fix: capitalised type' no-match
  assert_match subject "$p" 'fix - wrong separator' no-match
  assert_match subject "$p" 'fix(ci):no space after colon' no-match
  assert_match subject "$p" "fix: $(printf 'x%.0s' $(seq 1 73))" no-match
}

check_issue_reference_cases() {
  local p=$ISSUE_REFERENCE_PATTERN
  assert_match "issue ref" "$p" 'Closes #595' match
  assert_match "issue ref" "$p" 'Refs #12, and see #34' match
  assert_match "issue ref" "$p" 'Fixes https://github.com/z-shell/zi/issues/486' match
  assert_match "issue ref" "$p" 'follows z-shell/.github#590 for context' match
  assert_match "issue ref" "$p" 'see z-shell/zi#487' match

  # A body with no work item at all is the case ADR-0022 exists to catch: 10
  # of the last 60 merged pull requests looked like this.
  assert_match "issue ref" "$p" 'Tidies up the release script.' no-match
  assert_match "issue ref" "$p" '' no-match
  # A bare hash with no number, or an anchor-looking token, is not a reference.
  assert_match "issue ref" "$p" 'see section #overview' no-match
  assert_match "issue ref" "$p" 'issue #0 does not exist' no-match
}

# The failure mode behind #586: an empty pattern matches every line. If a
# regression ever lets an empty value reach grep, these prove it is caught.
check_empty_pattern_is_never_harmless() {
  assert_match "empty pattern" "" 'any line at all' match
  checks=$((checks + 1))
  [ -n "$TRAILER_PATTERN" ] || fail "extracted trailer pattern is empty"
  checks=$((checks + 1))
  [ -n "$BRANCH_PATTERN" ] || fail "extracted branch pattern is empty"
}

check_no_grep_q_on_trailer
check_fallbacks_present
check_no_input_defaults
check_exempt_label_is_canonical
check_prefixes_not_duplicated
check_branch_cases
check_trailer_cases
check_conventional_cases
check_issue_reference_cases
check_empty_pattern_is_never_harmless

if [ "$failures" -gt 0 ]; then
  printf '\n%d of %d checks failed\n' "$failures" "$checks" >&2
  exit 1
fi

printf '%d checks passed\n' "$checks"
