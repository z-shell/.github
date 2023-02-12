<h1> Z-Shell GitHub Organization </h1>

## Github Actions & Workflows

The set of [workflows](https://github.com/z-shell/.github/tree/main/workflow-templates) and [actions](https://github.com/z-shell/.github/tree/main/actions) for the organization to leverage GitHub’s collaborative capabilities and allow everyone in your organization who has permission to create workflows to do so more quickly and easily.

<div align="center">
 <p align="center">
  <a href="https://github.com/z-shell/.github/actions/new">
    <img align="center" src="https://raw.githubusercontent.com/z-shell/.github/main/.github/img/github_actions.png" alt="Z-Shell Github Actions" height="auto" width="70%" />
  </a>
  </p>
</div>

## Trunk

<div align="center">
 <p align="center">
  <a href="https://slack.trunk.io">
    <img align="center" src="https://user-images.githubusercontent.com/59910950/218301528-2a6de256-e767-4871-b67f-f2b3f4a2fa16.png" alt="Trunk App" height="auto" width="70%" />
  </a>
 </p>
  <p align="center">
    <a href="https://slack.trunk.io">
      <img align="center" src="https://img.shields.io/badge/slack-slack.trunk.io-blue?logo=slack"/>
    </a>
    <a href="https://docs.trunk.io">
      <img align="center" src="https://img.shields.io/badge/docs.trunk.io-7f7fcc?label=docs&logo=readthedocs&labelColor=555555&logoColor=ffffff"/>
    </a>
  </p>
</div>

### Get Started

- [📊 app.trunk.io/z-shell](https://app.trunk.io/z-shell)

Initialize it with (`trunk init`). All linters and formatters, as well as the version of Trunk itself, are versioned in `.trunk/trunk.yaml` ([configs](https://github.com/trunk-io/configs)).

1. Install Trunk → `curl https://get.trunk.io -fsSL | bash`
   ([docs](https://docs.trunk.io/get-started))
2. Setup Trunk in your repo → `trunk init` ([docs](https://docs.trunk.io/get-started))
3. Locally check your changes for issues → `trunk check`
   ([docs](https://docs.trunk.io/check/overview))
4. Locally format your changes → `trunk fmt` ([docs](https://docs.trunk.io/check/cli))
5. Make sure no lint and format issues leak onto `main`

Example preset of [.trunk/trunk.yaml](../.trunk/trunk.yaml):

## Renovate Mend

Example preset of [.github/renovate.json](https://github.com/z-shell/wiki/blob/main/.github/renovate.json):

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": ["local>z-shell/.github:renovate-config"]
}
```

<!--
<div align="center">
  <p>
    <a href="https://docs.renovatebot.com/">
      <img align="center" src="https://user-images.githubusercontent.com/59910950/218302002-477fbdc8-eda9-4e09-908b-35c777d48d17.jpg" alt="renovate" height="auto" width="50%" />
    </a>
  </p>
</div>
-->
