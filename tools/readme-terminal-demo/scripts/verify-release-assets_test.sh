#!/usr/bin/env bash

# Exercise release verification against real downloaded assets and mutations.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly VERIFIER="${SCRIPT_DIR}/verify-release-assets.sh"
readonly ASSETS_DIR="${1:?usage: verify-release-assets_test.sh ASSETS_DIR}"
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

make_case() {
  local name="$1"
  local directory="${WORK_DIR}/${name}"
  mkdir -p -- "${directory}"
  local asset
  for asset in cosign-linux-amd64 cosign-linux-amd64.sigstore.json checksums.txt checksums.txt.sigstore.json vhs_0.11.0_Linux_x86_64.tar.gz; do
    ln -s -- "${ASSETS_DIR}/${asset}" "${directory}/${asset}"
  done
  printf '%s\n' "${directory}"
}

checksum_case="$(make_case checksum)"
rm -- "${checksum_case}/checksums.txt"
cp -- "${ASSETS_DIR}/checksums.txt" "${checksum_case}/checksums.txt"
printf 'modified\n' >>"${checksum_case}/checksums.txt"
expect_failure 'modified checksum file' "${VERIFIER}" "${checksum_case}"

expect_failure 'wrong certificate identity' \
  "${ASSETS_DIR}/cosign-linux-amd64" verify-blob \
  --bundle "${ASSETS_DIR}/checksums.txt.sigstore.json" \
  --certificate-identity 'https://invalid.example/workflow.yml@refs/heads/main' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  "${ASSETS_DIR}/checksums.txt"

expect_failure 'wrong OIDC issuer' \
  "${ASSETS_DIR}/cosign-linux-amd64" verify-blob \
  --bundle "${ASSETS_DIR}/checksums.txt.sigstore.json" \
  --certificate-identity 'https://github.com/charmbracelet/meta/.github/workflows/goreleaser.yml@refs/heads/main' \
  --certificate-oidc-issuer 'https://invalid.example' \
  "${ASSETS_DIR}/checksums.txt"

bundle_case="$(make_case bundle)"
rm -- "${bundle_case}/checksums.txt.sigstore.json"
cp -- "${ASSETS_DIR}/checksums.txt.sigstore.json" "${bundle_case}/checksums.txt.sigstore.json"
printf 'modified\n' >>"${bundle_case}/checksums.txt.sigstore.json"
expect_failure 'modified Sigstore bundle' "${VERIFIER}" "${bundle_case}"

tar_case="$(make_case tar)"
rm -- "${tar_case}/vhs_0.11.0_Linux_x86_64.tar.gz"
cp -- "${ASSETS_DIR}/vhs_0.11.0_Linux_x86_64.tar.gz" "${tar_case}/vhs_0.11.0_Linux_x86_64.tar.gz"
printf 'modified\n' >>"${tar_case}/vhs_0.11.0_Linux_x86_64.tar.gz"
expect_failure 'modified VHS archive' "${VERIFIER}" "${tar_case}"
