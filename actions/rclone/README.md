# Github Action - `rclone`

Run [rclone](https://rclone.org) to sync files and directories from different cloud storage providers.

## Usage

```yaml
---
name: "🔄 Rclone"
on:
  push:
    paths:
      - "static/**"
  workflow_dispatch: {}

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sync:
    if: github.repository == 'z-shell/wiki'
    runs-on: ubuntu-latest
    environment: R2
    env:
      sync_path: static
      remote_path: "r2store:r2-store/public"
    steps:
      - name: "⤵️ Check out code from GitHub"
        uses: actions/checkout@v3
      - name: "⏫ Run rclone"
        uses: z-shell/.github/actions/rclone@v1.0.0
        with:
          # Configuration to set up for rclone (required)
          config: ${{ secrets.R2_STORE }}
          # Pass any argumets supported by rclone (required)
          args: "sync ${{ env.sync_path }} ${{ env.remote_path }}"
          # Set custom location for rclone configuration file (optional)
          config-file: ""
          # Verbose debugging and logging or carry on, but do quit on errors (optional)
          debug: false
```

> - `config` can be omitted if [CLI arguments](https://rclone.org/flags/#backend-flags) or [environment variables](https://rclone.org/docs/#environment-variables) are supplied.
>   - can also be encrypted if [`RCLONE_CONFIG_PASS`](https://rclone.org/docs/#configuration-encryption) secret is set.
> - `args` pass any argumets supported by `rclone`.
> - `config-file` set custom location for `rclone` configuration file.
> - `debug` verbose debugging and logging or carry on, but do quit on errors.
