#!/usr/bin/env bash

# Verify the reusable bootstrap runs only the verified extracted GitHub CLI.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly BOOTSTRAP="${SCRIPT_DIR}/bootstrap-gh.sh"
readonly ASSETS_DIR="${1:?usage: bootstrap-gh_test.sh ASSETS_DIR}"

output="$(README_TERMINAL_DEMO_GH_ASSET_DIR="${ASSETS_DIR}" "${BOOTSTRAP}" version)"
[[ "${output}" == gh\ version\ 2.96.0* ]]
