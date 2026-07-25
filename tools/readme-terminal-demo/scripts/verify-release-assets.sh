#!/usr/bin/env bash

# Verify the cosign bootstrap and VHS release bytes before any extraction.

set -euo pipefail

readonly ASSETS_DIR="${1:?usage: verify-release-assets.sh ASSETS_DIR}"

(
  cd -- "${ASSETS_DIR}"

  printf '%s  %s\n' \
    'c956e5dfcac53d52bcf058360d579472f0c1d2d9b69f55209e256fe7783f4c74' \
    'cosign-linux-amd64' | sha256sum -c -
  printf '%s  %s\n' \
    'b3a04913f3a3f4a38e4a7a42b8d590834b8791de99ddeaad66c608b6aa8e02a4' \
    'cosign-linux-amd64.sigstore.json' | sha256sum -c -
  printf '%s  %s\n' \
    '71b7e8eb9742c1d8bad844980dd00bf665743a0321d1a32832d24a6e371952f2' \
    'checksums.txt' | sha256sum -c -
  printf '%s  %s\n' \
    'a4e998a04e9a0e43a7bf6a6180a0a83801bf6fb8b3ca88c7f2ba4f8255955128' \
    'checksums.txt.sigstore.json' | sha256sum -c -
  printf '%s  %s\n' \
    '99cb634587eaae0473c1ea377db80c3a048c27f99fe0a7febb1a1e8cb7ee5009' \
    'vhs_0.11.0_Linux_x86_64.tar.gz' | sha256sum -c -

  chmod +x -- cosign-linux-amd64
  ./cosign-linux-amd64 verify-blob \
    --bundle cosign-linux-amd64.sigstore.json \
    --certificate-identity 'keyless@projectsigstore.iam.gserviceaccount.com' \
    --certificate-oidc-issuer 'https://accounts.google.com' \
    cosign-linux-amd64
  ./cosign-linux-amd64 verify-blob \
    --bundle checksums.txt.sigstore.json \
    --certificate-identity 'https://github.com/charmbracelet/meta/.github/workflows/goreleaser.yml@refs/heads/main' \
    --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
    checksums.txt
  grep -Fx '99cb634587eaae0473c1ea377db80c3a048c27f99fe0a7febb1a1e8cb7ee5009  vhs_0.11.0_Linux_x86_64.tar.gz' checksums.txt
  printf '%s  %s\n' \
    '99cb634587eaae0473c1ea377db80c3a048c27f99fe0a7febb1a1e8cb7ee5009' \
    'vhs_0.11.0_Linux_x86_64.tar.gz' | sha256sum -c -
)
