# Github Action - `rclone`

Run [rclone](https://rclone.org) to sync files and directories from different cloud storage providers.

## Usage

```yaml
---
name: "🔄 Rclone"
# Working example: https://github.com/z-shell/wiki/blob/main/.github/workflows/rclone.yml
on:
  push:
    paths:
      # Paths which will tigger workflow
      - "static/**"
  workflow_dispatch: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sync:
    # Limit to specific repository. (e.g: z-shell/wiki)
    #if: github.repository == 'org-or-user/repository-name'
    runs-on: ubuntu-latest
    environment: rclone
    env:
      # Set paths to be used as arguments to pass for rclone.
      # Source path (some/path/to/source)
      local_path: ""
      # Remote path (remote:some/remote/path
      remote_path: ""
    steps:
      - name: "⤵️ Check out code from GitHub"
        uses: actions/checkout@v3
      - name: "⏫ Run rclone"
        uses: z-shell/.github/actions/rclone@v1.0.0
        with:
          # The RCLONE_CONFIG secret must be set to set up for rclone (required)
          config: ${{ secrets.RCLONE_CONFIG }}
          # Pass any argumets supported by rclone (required)
          args: "sync ${{ env.local_path }} ${{ env.remote_path }}"
          # Set custom location for rclone configuration file (optional)
          # Will try to detect the default location using rclone.
          #config-file: ""
          # Verbose debugging and logging or carry on, but do quit on errors (optional)
          debug: false
```

> - `config` can be omitted if [CLI arguments](https://rclone.org/flags/#backend-flags) or [environment variables](https://rclone.org/docs/#environment-variables) are supplied.
>   - can also be encrypted if [`RCLONE_CONFIG_PASS`](https://rclone.org/docs/#configuration-encryption) secret is set.
> - `args` pass any argumets supported by `rclone`.
> - `config-file` set custom location for `rclone` configuration file.
> - `debug` verbose debugging and logging or carry on, but do quit on errors.
