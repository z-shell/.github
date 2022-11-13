# GitHub Action - SSH Mirror

## Example workflow

```yml
name: "SSH Mirror"

on:
  push:
  delete:
  create:
  workflow_dispatch:
    inputs:
      dry-run:
        description: "Manually dispatch dry-run: [true/false]"
        required: true
        default: "false"

concurrency:
  group: ssh-mirror-${{ github.ref }}

jobs:
  ssh-mirror:
    runs-on: ubuntu-latest
    environment: ssh-mirror
    steps:
      - uses: z-shell/.github/actions/mirror@main
        env:
          # SSH private key with access to both repositories (required).
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
          # Known hosts as used in the 'known_hosts' file (optional).
          SSH_KNOWN_HOSTS: ${{ secrets.SSH_KNOWN_HOSTS }}
        with:
          # SSH URL of the source repository (required).
          source: "git@example1.com:user/repo.git"
          # SSH URL of the target repository (required).
          target: "git@example2.com:user/repo.git"
          # Do not apply any changes (optional).
          dry-run: false
```

## Docker

```sh
docker run --rm -e "SSH_PRIVATE_KEY=$(cat ~/.ssh/id_rsa)" $(docker build -q .) "$SOURCE_REPO" "$DESTINATION_REPO"
```

## Environment

`SSH_PRIVATE_KEY`: Create a [SSH key](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent#generating-a-new-ssh-key) **without** a passphrase which has access to both repositories. On GitHub you can add the public key as [a deploy key to the repository](https://docs.github.com/en/developers/overview/managing-deploy-keys#deploy-keys). GitLab has also [deploy keys with write access](https://docs.gitlab.com/ee/user/project/deploy_keys/) and for any other services you may have to add the public key to your personal account.  
Store the private key as [an encrypted secret](https://docs.github.com/en/actions/reference/encrypted-secrets) and use it in your workflow as seen in the example workflow below.

`SSH_KNOWN_HOSTS`: Known hosts as used in the `known_hosts` file. _StrictHostKeyChecking_ is disabled in case the variable isn't available. If you added the private key or known hosts in an [environment](https://docs.github.com/en/actions/reference/environments) make sure to [reference the environment name in your workflow](https://docs.github.com/en/actions/reference/workflow-syntax-for-github-actions#jobsjob_idenvironment) otherwise the secret is not passed to the workflow.
