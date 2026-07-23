#!/usr/bin/env bash

# Download, verify, extract, and invoke the one approved GitHub CLI binary.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly GH_TAR_URL='https://github.com/cli/cli/releases/download/v2.96.0/gh_2.96.0_linux_amd64.tar.gz'
readonly GH_TAR_SHA256='83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60'
readonly GH_CHECKSUMS_URL='https://github.com/cli/cli/releases/download/v2.96.0/gh_2.96.0_checksums.txt'
readonly GH_CHECKSUMS_SHA256='fc046371efa250e2875208341a786a35a01717d5eebec6903e199a9b8a3f3565'
readonly WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "${WORK_DIR}"' EXIT

if [[ -n "${README_TERMINAL_DEMO_GH_ASSET_DIR:-}" ]]; then
  cp -- "${README_TERMINAL_DEMO_GH_ASSET_DIR}/gh_2.96.0_linux_amd64.tar.gz" "${WORK_DIR}/"
  cp -- "${README_TERMINAL_DEMO_GH_ASSET_DIR}/gh_2.96.0_checksums.txt" "${WORK_DIR}/"
else
  curl --fail --location --silent --show-error \
    --output "${WORK_DIR}/gh_2.96.0_linux_amd64.tar.gz" "${GH_TAR_URL}"
  curl --fail --location --silent --show-error \
    --output "${WORK_DIR}/gh_2.96.0_checksums.txt" "${GH_CHECKSUMS_URL}"
fi

# Keep the embedded literals visible for the central parity check.
[[ "${GH_TAR_SHA256}" == '83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60' ]]
[[ "${GH_CHECKSUMS_SHA256}" == 'fc046371efa250e2875208341a786a35a01717d5eebec6903e199a9b8a3f3565' ]]
"${SCRIPT_DIR}/verify-gh-assets.sh" "${WORK_DIR}" >&2

tar -xzf "${WORK_DIR}/gh_2.96.0_linux_amd64.tar.gz" -C "${WORK_DIR}"
"${WORK_DIR}/gh_2.96.0_linux_amd64/bin/gh" "$@"
