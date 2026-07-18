#!/usr/bin/env bash

# Verify the contributor Go wrapper uses the immutable toolchain and mounts.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly WRAPPER="${SCRIPT_DIR}/in-go-image.sh"
readonly GO_DIGEST='sha256:117e07f49461abb984fc8aef661432461ff43d06faa22c3b73af6a49ce325cb9'

grep -Fq -- "${GO_DIGEST}" "${WRAPPER}"

version="$(${WRAPPER} go version)"
[[ "${version}" == 'go version go1.26.5 linux/amd64' ]]

if "${WRAPPER}" sh -c 'printf blocked > /src/.read-only-probe'; then
  echo 'expected the /src write probe to fail' >&2
  exit 1
fi

"${WRAPPER}" sh -c 'probe=/tmp/readme-terminal-demo-write-probe; printf allowed > "$probe"; test "$(cat "$probe")" = allowed; rm -f -- "$probe"'
