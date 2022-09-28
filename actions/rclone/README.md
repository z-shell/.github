# Github Action - Rclone

Run [rclone](https://rclone.org) to sync files and directories from different cloud storage providers.

## Usage

```yaml
---
name: "🔄 Rclone"
on:
  push:
    branches: [main]
    tags: ["v*.*.*"]
  schedule:
    - cron: "0 07 * * 5"
  workflow_dispatch: {}

jobs:
  rclone:
    runs-on: ubuntu-latest
    steps:
      - name: "⤵️ Check out code from GitHub"
        uses: actions/checkout@v3
      - name: "⏫ Rclone"
        uses: z-shell/.github/actions/rclone@main
        with:
          # Configuration for rclone (required)
          RCLONE_CONF: ${{ secrets.R2_STORE }}
          # Run required arguments with rclone (required)
          RUN: sync static r2store:r2-store/public
          # Default PATH to rclone configuration (optional)
          #RCLONE_CONF_PATH: "${HOME}/.config/rclone"
```

`RCLONE_CONF` can be omitted if [CLI arguments](https://rclone.org/flags/#backend-flags) or [environment variables](https://rclone.org/docs/#environment-variables) are supplied. `RCLONE_CONF` can also be encrypted if [`RCLONE_CONFIG_PASS`](https://rclone.org/docs/#configuration-encryption) secret is supplied.
