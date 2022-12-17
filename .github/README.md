<h1> Z-Shell GitHub Organization </h1>

## Trunk

  <a href="https://slack.trunk.io">
    <img src="https://img.shields.io/badge/slack-slack.trunk.io-blue?logo=slack"/>
  </a>
  <a href="https://docs.trunk.io">
    <img src="https://img.shields.io/badge/docs.trunk.io-7f7fcc?label=docs&logo=readthedocs&labelColor=555555&logoColor=ffffff"/>
  </a>

### Get Started

Initialize it with (`trunk init`). All linters and formatters, as well as the version of Trunk itself, are versioned in `.trunk/trunk.yaml` ([configs](https://github.com/trunk-io/configs)).

1. Install Trunk → `curl https://get.trunk.io -fsSL | bash`
   ([docs](https://docs.trunk.io/get-started))
2. Setup Trunk in your repo → `trunk init` ([docs](https://docs.trunk.io/get-started))
3. Locally check your changes for issues → `trunk check`
   ([docs](https://docs.trunk.io/check/overview))
4. Locally format your changes → `trunk fmt` ([docs](https://docs.trunk.io/check/cli))
5. Make sure no lint and format issues leak onto `main`

Example preset of [.trunk/trunk.yaml](../.trunk/trunk.yaml):

```yaml
version: 0.1
cli:
  version: 1.2.1
  options:
    - commands: [ALL]
      args: --monitor=true
    - commands: [check, fmt]
    - args: -y
repo:
  repo:
    host: github.com
    owner: z-shell
    name: .github
plugins:
  sources:
    - id: trunk
      uri: https://github.com/trunk-io/plugins
      ref: v0.0.8
      import_to_global: true
lint:
  enabled:
    - oxipng@7.0.0
    - svgo@3.0.2
    - git-diff-check@SYSTEM
    - actionlint@1.6.22
    - gitleaks@8.15.2
    - markdownlint@0.32.2
    - prettier@2.8.1
    - shfmt@3.5.0
runtimes:
  enabled:
    - go@1.18.3
    - node@16.14.2
actions:
  enabled:
    - trunk-upgrade-available
    - trunk-fmt-pre-commit
    - trunk-check-pre-push
    - trunk-cache-prune
    - trunk-announce
```

## Renovate Mend

Example preset of [.github/renovate.json](https://github.com/z-shell/wiki/blob/main/.github/renovate.json):

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

Store Renovate configuration as above in one of these locations:

```verilog
renovate.json
renovate.json5
.github/renovate.json
.github/renovate.json5
.gitlab/renovate.json
.gitlab/renovate.
.renovaterc
.renovaterc.json
package.json (within a "renovate" section)
```
