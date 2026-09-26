# Setup Zsh

Set up Zsh for GitHub Actions. Pin this action to a full commit SHA when using it from another repository, following the [organization workflow conventions](../../.github/instructions/github-actions-ci-cd-best-practices.instructions.md).

## Version contract

| Input                       | Linux                        | macOS            | Windows            |
| --------------------------- | ---------------------------- | ---------------- | ------------------ |
| omitted, empty, or `latest` | Ubuntu package               | Homebrew package | Chocolatey package |
| `5.9` or `5.9.2`            | Checksum-pinned source build | Fails explicitly | Fails explicitly   |
| other values                | Fails explicitly             | Fails explicitly | Fails explicitly   |

`latest` retains the package manager's available version. It does not promise the latest upstream release. Explicit versions never fall back to a package version.

Linux source installs require an Ubuntu/Debian runner with `sudo apt-get`. The action installs build prerequisites, verifies the archive against a checked-in SHA-256 digest (including after upstream moves it into the old-release directory), and builds with multibyte support. It installs the binary, modules, and completion functions into a unique directory under `RUNNER_TEMP`, verifies the installed version, and adds its `bin` directory to `GITHUB_PATH` for subsequent steps. The system shell is not replaced. Man pages and optional development-library integrations such as PCRE are outside this install contract. Builds are not cached.

For example, after checking out this repository:

```yaml
- uses: ./actions/setup-zsh
  with:
    version: "5.9.2"
- name: Verify native oracle
  shell: bash
  run: zsh --version
```

Request an exact version in native-oracle jobs. Compatibility jobs choose their own versions; this action does not impose an organization-wide minimum. Existing SHA-pinned callers must update their action reference before receiving this behavior. The reusable `zsh-ci.yml` action reference also requires a separately reviewed pin update.

## Source pins and verification

`install.sh` owns the supported source versions and their hashes. The 5.9 archive is published in the [official old-release directory](https://www.zsh.org/pub/old/); the 5.9.2 digest is published in the [official SHA256SUM file](https://www.zsh.org/pub/SHA256SUM). Verify release bytes and review compatibility before adding a version. Keep this table, action input description, and smoke matrix consistent.

Run the installer regressions without network access or package installation:

```sh
python3 -m unittest scripts/test_setup_zsh.py -v
bash -n actions/setup-zsh/install.sh
shellcheck -s bash actions/setup-zsh/install.sh
actionlint .github/workflows/setup-zsh-test.yml
```

The `Setup Zsh Tests` workflow also installs each supported version on an Ubuntu runner and verifies the selected binary, a dynamic module, and completion initialization. Hosted checks are required evidence for the action's real runner behavior; mocked regressions alone do not establish installation success.
