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

jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: "⤵️ Check out code from GitHub"
        uses: actions/checkout@v3
      - name: "⏫ Rclone"
      uses: z-shell/.github/actions/rclone@main
      env:
        RCLONE_CONF: ${{ secrets.RCLONE_CONF }}
      with:
        args: copy <source>:<source_path> <dest>:<dest_path>
```

`RCLONE_CONF` can be omitted if [CLI arguments](https://rclone.org/flags/#backend-flags) or [environment variables](https://rclone.org/docs/#environment-variables) are supplied. `RCLONE_CONF` can also be encrypted if [`RCLONE_CONFIG_PASS`](https://rclone.org/docs/#configuration-encryption) secret is supplied.
