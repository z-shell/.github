#!/usr/bin/env bash

# Prove the pinned GitHub CLI bootstrap rejects modified release metadata/data.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly VERIFIER="${SCRIPT_DIR}/verify-gh-assets.sh"
readonly ASSETS_DIR="${1:?usage: verify-gh-assets_test.sh ASSETS_DIR}"
readonly WORK_DIR="$(mktemp -d)"
trap 'rm -rf -- "${WORK_DIR}"' EXIT

"${VERIFIER}" "${ASSETS_DIR}"

expect_failure() {
  local label="$1"
  shift
  if "$@"; then
    echo "expected ${label} to fail" >&2
    exit 1
  fi
}

checksum_case="${WORK_DIR}/checksum"
mkdir -p -- "${checksum_case}"
cp -- "${ASSETS_DIR}/gh_2.96.0_checksums.txt" "${checksum_case}/gh_2.96.0_checksums.txt"
ln -s -- "${ASSETS_DIR}/gh_2.96.0_linux_amd64.tar.gz" "${checksum_case}/gh_2.96.0_linux_amd64.tar.gz"
printf 'modified\n' >>"${checksum_case}/gh_2.96.0_checksums.txt"
expect_failure 'modified GitHub CLI checksum file' "${VERIFIER}" "${checksum_case}"

tar_case="${WORK_DIR}/tar"
mkdir -p -- "${tar_case}"
ln -s -- "${ASSETS_DIR}/gh_2.96.0_checksums.txt" "${tar_case}/gh_2.96.0_checksums.txt"
cp -- "${ASSETS_DIR}/gh_2.96.0_linux_amd64.tar.gz" "${tar_case}/gh_2.96.0_linux_amd64.tar.gz"
printf 'modified\n' >>"${tar_case}/gh_2.96.0_linux_amd64.tar.gz"
expect_failure 'modified GitHub CLI archive' "${VERIFIER}" "${tar_case}"
