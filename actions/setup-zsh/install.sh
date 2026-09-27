#!/usr/bin/env bash
# Standalone GitHub Actions installer, Bash 3.2+.
set -euo pipefail

version=${ZSH_VERSION:-latest}
patch_set=${ZSH_PATCH_SET:-none}
action_dir=${SETUP_ZSH_ACTION_PATH:-$(cd -- "$(dirname -- "$0")" && pwd)}
case ${patch_set}:${version} in
none:*) ;;
trap-bounds-a3547fd4:5.9.2) ;;
*)
  printf '%s\n' 'Unsupported Zsh patch-set/version combination.' >&2
  exit 1
  ;;
esac
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

if [[ ${RUNNER_OS} == Windows ]]; then
  printf '%s\n' 'Exact Zsh versions are supported only on Linux and macOS; use latest for package installs.' >&2
  exit 1
fi

# Checked against the official release archives. Keep digests in source so a
# changed download cannot silently change the shell used by native oracles.
case ${version} in
5.8.1)
  url=https://www.zsh.org/pub/old/zsh-5.8.1.tar.xz
  digest=b6973520bace600b4779200269b1e5d79e5f505ac4952058c11ad5bbf0dd9919
  ;;
5.9)
  url=https://www.zsh.org/pub/old/zsh-5.9.tar.xz
  digest=9b8d1ecedd5b5e81fbf1918e876752a7dd948e05c1a0dba10ab863842d45acd5
  ;;
5.9.2)
  url=https://www.zsh.org/pub/zsh-5.9.2.tar.xz
  digest=36fa734374b44783582cec09bcd67822e2f992c779ec1624ab5596df078d2f81
  ;;
*)
  printf '%s\n' 'Unsupported Zsh version; supported values: latest, 5.8.1, 5.9, 5.9.2.' >&2
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

cflags=-O2
dllflags=''
configure_args=(--enable-multibyte --with-tcsetpgrp)
cppflags=''
ldflags=''
patch_tool="patch"
hash_tool=(sha256sum)
if [[ ${RUNNER_OS} == Linux ]]; then
  sudo apt-get update
  sudo apt-get install -y build-essential libncurses-dev curl ca-certificates xz-utils patch python3
else
  brew install ncurses xz gpatch
  ncurses_prefix=$(brew --prefix ncurses)
  cppflags="-I${ncurses_prefix}/include"
  ldflags="-L${ncurses_prefix}/lib"
  patch_tool=gpatch
  # Match upstream's modern Darwin linker mode (383526da422c).
  dllflags='-bundle -flat_namespace -undefined dynamic_lookup'
  configure_args+=("DLLDFLAGS=${dllflags}")
  hash_tool=(shasum -a 256)
fi
# Older release configure probes use C89 constructs that new compilers reject:
# implicit int under Clang, and GCC 14+ incompatible-pointer-types, which makes
# the termcap boolcodes probe fail so termcap.c redefines the ncurses symbol.
if [[ ${version} == 5.8.1 || ${version} == 5.9 ]]; then
  cflags='-O2 -std=gnu89'
fi
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
printf '%s  %s\n' "${digest}" "${build_dir}/zsh.tar.xz" | "${hash_tool[@]}" --check --status
patch_digest=''
patch_commit=''
if [[ ${patch_set} != none ]]; then
  patch_digest=bcac19bbbb4506ae35eee6e7873c4308aba9b86e4e6d152101e3a4c4d5265255
  patch_commit=a3547fd4c165bd6c0c9c9d2643bd61b593f7bbaf
  printf '%s  %s\n' "${patch_digest}" "${action_dir}/${patch_set}.patch" | "${hash_tool[@]}" --check --status
fi
# Extract only after verifying the release bytes.
tar -xJf "${build_dir}/zsh.tar.xz" -C "${build_dir}"
(
  cd "${build_dir}/zsh-${version}"
  if [[ ${patch_set} != none ]]; then
    "${patch_tool}" --batch --forward --fuzz=0 -p1 --dry-run <"${action_dir}/${patch_set}.patch"
    "${patch_tool}" --batch --forward --fuzz=0 -p1 <"${action_dir}/${patch_set}.patch"
  fi
  CC=cc CFLAGS="${cflags}" CPPFLAGS="${cppflags}" LDFLAGS="${ldflags}" ./configure --prefix="${install_dir}" "${configure_args[@]}"
  make -j2
  if [[ ${patch_set} != none ]]; then
    make TESTNUM=A05 check
    make TESTNUM=B11 check
  fi
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
"${install_dir}/bin/zsh" -f -c 'zmodload zsh/system'
profile="${version}+${patch_set}"
python3 "${action_dir}/provenance.py" "${install_dir}" "${version}" "${profile}" \
  "${url}" "${digest}" "${patch_commit}" "${patch_digest}" "${cppflags}" "${ldflags}" "${cflags}" "${dllflags}"
if [[ -n ${GITHUB_OUTPUT-} ]]; then
  {
    printf 'executable=%s\n' "${install_dir}/bin/zsh"
    printf 'profile=%s\n' "${profile}"
    printf 'provenance=%s\n' "${install_dir}/provenance.json"
  } >>"${GITHUB_OUTPUT}" || exit 1
fi
printf '%s\n' "${install_dir}/bin" >>"${GITHUB_PATH}"
installed=true
