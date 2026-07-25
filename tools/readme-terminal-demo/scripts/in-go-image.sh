#!/usr/bin/env bash

# Run contributor Go commands in the immutable project toolchain.

set -euo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly TOOL_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly GO_IMAGE='golang:1.26.5-trixie@sha256:117e07f49461abb984fc8aef661432461ff43d06faa22c3b73af6a49ce325cb9'

exec docker run --rm \
  --platform linux/amd64 \
  --volume "${TOOL_DIR}:/src:ro" \
  --workdir /src \
  "${GO_IMAGE}" \
  "$@"
