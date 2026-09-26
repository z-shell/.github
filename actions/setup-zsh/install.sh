#!/usr/bin/env bash
# Standalone GitHub Actions installer, Bash 3.2+.
set -euo pipefail

version=${ZSH_VERSION:-latest}
case ${RUNNER_OS:?RUNNER_OS is required} in
Linux | macOS | Windows) ;;
*)
  printf '%s\n' 'Unsupported runner OS.' >&2
  exit 1
  ;;
esac

if [[ ${version} == latest ]]; then
  case ${RUNNER_OS} in
  Linux)
    sudo apt-get update
    sudo apt-get install -y zsh
    ;;
  macOS) brew install zsh ;;
  Windows) choco install zsh ;;
  *) exit 1 ;;
  esac
  zsh --version
  exit 0
fi

if [[ ${RUNNER_OS} != Linux ]]; then
  printf '%s\n' 'Exact Zsh versions are supported only on Linux; use latest for package installs.' >&2
  exit 1
fi

# Checked against the official release archives. Keep digests in source so a
# changed download cannot silently change the shell used by native oracles.
case ${version} in
5.9)
  url=https://www.zsh.org/pub/old/zsh-5.9.tar.xz
  digest=9b8d1ecedd5b5e81fbf1918e876752a7dd948e05c1a0dba10ab863842d45acd5
  ;;
5.9.2)
  url=https://www.zsh.org/pub/zsh-5.9.2.tar.xz
  digest=36fa734374b44783582cec09bcd67822e2f992c779ec1624ab5596df078d2f81
  ;;
*)
  printf '%s\n' 'Unsupported Zsh version; supported values: latest, 5.9, 5.9.2.' >&2
  exit 1
  ;;
esac

: "${RUNNER_TEMP:?RUNNER_TEMP is required}" "${GITHUB_PATH:?GITHUB_PATH is required}"
build_dir=$(mktemp -d "${RUNNER_TEMP}/setup-zsh-build.XXXXXX")
install_dir=''
installed=false
cleanup() {
  rm -r -- "${build_dir}"
  if [[ ${installed} == false && -n ${install_dir} ]]; then
    rm -r -- "${install_dir}"
  fi
}
trap cleanup EXIT
install_dir=$(mktemp -d "${RUNNER_TEMP}/setup-zsh-install.XXXXXX")

sudo apt-get update
sudo apt-get install -y build-essential libncurses-dev curl ca-certificates xz-utils
download_release() {
  curl --fail --show-error --silent --location --proto '=https' --proto-redir '=https' \
    --retry 3 --output "${build_dir}/zsh.tar.xz" "$1"
}
# Upstream moves superseded stable releases into old/. Both locations must
# satisfy the same checked-in digest; this never changes the requested version.
# download_release returns curl status directly; it does not rely on errexit.
# shellcheck disable=SC2310
if ! download_release "${url}"; then
  download_release "https://www.zsh.org/pub/old/zsh-${version}.tar.xz"
fi
printf '%s  %s\n' "${digest}" "${build_dir}/zsh.tar.xz" | sha256sum --check --status
# Extract only after verifying the release bytes.
tar -xJf "${build_dir}/zsh.tar.xz" -C "${build_dir}"
(
  cd "${build_dir}/zsh-${version}"
  ./configure --prefix="${install_dir}" --enable-multibyte --with-tcsetpgrp
  make -j2
  make install.bin install.modules install.fns
)
# The child Zsh, not Bash, expands its own version parameter.
# shellcheck disable=SC2016
actual_version=$("${install_dir}/bin/zsh" -f -c 'printf "%s" "${ZSH_VERSION}"')
if [[ ${actual_version} != "${version}" ]]; then
  printf '%s\n' 'Installed Zsh does not match the requested version.' >&2
  exit 1
fi
"${install_dir}/bin/zsh" --version
printf '%s\n' "${install_dir}/bin" >>"${GITHUB_PATH}"
installed=true
