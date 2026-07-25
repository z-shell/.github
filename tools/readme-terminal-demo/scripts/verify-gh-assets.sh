#!/usr/bin/env bash

# Verify the pinned GitHub CLI release bytes before extraction.

set -euo pipefail

readonly ASSETS_DIR="${1:?usage: verify-gh-assets.sh ASSETS_DIR}"

(
  cd -- "${ASSETS_DIR}"
  printf '%s  %s\n' \
    'fc046371efa250e2875208341a786a35a01717d5eebec6903e199a9b8a3f3565' \
    'gh_2.96.0_checksums.txt' | sha256sum -c -
  grep -Fx '83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60  gh_2.96.0_linux_amd64.tar.gz' gh_2.96.0_checksums.txt
  printf '%s  %s\n' \
    '83d5c2ccad5498f58bf6368acb1ab32588cf43ab3a4b1c301bf36328b1c8bd60' \
    'gh_2.96.0_linux_amd64.tar.gz' | sha256sum -c -
)
