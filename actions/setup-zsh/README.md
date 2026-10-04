<!-- GENERATED from knowledge/domains/ci/setup-zsh-action.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# Setup Zsh

Set up Zsh for GitHub Actions. Pin this action to a full commit SHA when using it from another repository, following the [organization workflow conventions](../../.github/instructions/ci/workflow-contract.instructions.md).

## Version contract

| Input                       | Linux                        | macOS                        | Windows            |
| --------------------------- | ---------------------------- | ---------------------------- | ------------------ |
| omitted, empty, or `latest` | Ubuntu package               | Homebrew package             | Chocolatey package |
| `5.8.1`, `5.9`, `5.9.2`     | Checksum-pinned source build | Checksum-pinned source build | Fails explicitly   |
| other values                | Fails explicitly             | Fails explicitly             | Fails explicitly   |

`latest` retains the package manager's available version. It does not promise the latest upstream release. Explicit versions never fall back to a package version.

Linux source installs require an Ubuntu/Debian runner with `sudo apt-get`. macOS source installs require Xcode command-line tools, Homebrew and Python 3; the action installs ncurses, xz and GNU patch. The installer supports Bash 3.2+. On Linux and macOS, 5.8.1 and 5.9 compile in GNU C89 mode because current GCC and Clang reject their legacy configure probes; on macOS, dynamic modules use the modern Darwin linker mode from [upstream 383526da422c](https://github.com/zsh-users/zsh/commit/383526da422cf1c962d9be7e9e6ac166e226bf2b). These flags are recorded in provenance. The action installs build prerequisites, verifies the archive against a checked-in SHA-256 digest (including after upstream moves it into the old-release directory), and builds with multibyte support. It installs the binary, modules, and completion functions into a unique directory under `RUNNER_TEMP`, verifies the installed version, and adds its `bin` directory to `GITHUB_PATH` for subsequent steps. The system shell is not replaced. Man pages and optional development-library integrations such as PCRE are outside this install contract. Builds are not cached.

For example, after checking out this repository:

```yaml
- uses: ./actions/setup-zsh
  with:
    version: "5.9.2"
- name: Verify native oracle
  shell: bash
  run: zsh --version
```

Request an exact version in native-oracle jobs. Compatibility jobs choose their own versions; this action does not impose an organization-wide minimum. Existing SHA-pinned callers must update their action reference before receiving this behavior. The reusable `zsh-ci.yml` workflow forwards its `zsh-version` input to this action; existing workflow callers must update their workflow SHA pin to receive exact installs.

## Source pins and verification

`install.sh` owns the supported source versions and their hashes. The 5.9 archive is published in the [official old-release directory](https://www.zsh.org/pub/old/); the 5.9.2 digest is published in the [official SHA256SUM file](https://www.zsh.org/pub/SHA256SUM). Verify release bytes and review compatibility before adding a version. Keep this table, action input description, and smoke matrix consistent.

Run the installer regressions without network access or package installation:

```sh
python3 -m unittest automation/ci/test_setup_zsh.py -v
bash -n actions/setup-zsh/install.sh
shellcheck -s bash actions/setup-zsh/install.sh
actionlint .github/workflows/setup-zsh-test.yml
```

The `Setup Zsh Tests` workflow also installs each exact supported version on Ubuntu and macOS runners and verifies the selected binary, a dynamic module, and completion initialization. Hosted checks are required evidence for the action's real runner behavior; mocked regressions alone do not establish installation success.

## Explicit patch profile

`patch-set` defaults to `none`. Only `version: "5.9.2"` with `patch-set: trap-bounds-a3547fd4` selects the reviewed numeric trap bounds correction from [upstream a3547fd4](https://github.com/zsh-users/zsh/commit/a3547fd4c165bd6c0c9c9d2643bd61b593f7bbaf). Unsupported combinations fail. The checked-in patch contains the two C-file changes, under the [Zsh license](ZSH-LICENSE.txt), and is SHA-256 verified before application without fuzz. No arbitrary patch URLs are accepted. Patched installs run upstream A05 and B11 tests before publication to the job.

```yaml
- uses: ./actions/setup-zsh
  id: runtime
  with:
    version: "5.9.2"
    patch-set: trap-bounds-a3547fd4
- name: Use the selected runtime
  env:
    ZSH_EXECUTABLE: ${{ steps.runtime.outputs.executable }}
  run: '"$ZSH_EXECUTABLE" --version'
```

The version string remains `5.9.2`; the distinct profile is `5.9.2+trap-bounds-a3547fd4`. Success with this profile does not qualify unpatched 5.9.2. Adoption is opt-in and does not enable native-oracle callers or change required checks.

Exact source builds expose `executable`, `profile` and `provenance` outputs. `provenance` points to JSON recording archive and patch hashes, action source hashes and GitHub action ref (empty for local invocation), OS, architecture, compiler, controlled build flags and installed executable hash. Retain that file with qualification logs. These are auditable inputs and artifact identities, not a claim of bit-for-bit reproducibility across runner images. Package-based `latest` installs leave these outputs empty.

The native smoke matrix covers all exact versions on Linux and macOS, plus the opt-in patch on both platforms. Installer regressions also run under macOS Bash 3.2. To roll back, restore the previous reviewed action SHA/profile and withdraw the affected qualification claim. A future upstream fix requires a separately reviewed exact release profile; this patch profile never silently changes source.
