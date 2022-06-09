# GitHub Action for Git commit

This Action for git commits any changed files and pushes those changes back to the origin repository.

## Usage

An example workflow to commit and push any changes back to the GitHub origin repository:

```YAML
name: Grunt build and commit updated stylesheets

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Commit changes
        uses: elstudio/actions-js-build/commit@v4
        with:
          commitMessage: Regenerate css
```

### Inputs

- `commitMessage` - **Optional**. Git commit message. Defaults to "Regenerate build artifacts."
- `commitUserEmail` **Optional**. Git commit user email. Defaults to "$GITHUB_ACTOR@users.noreply.github.com"
- `commitUserName` **Optional**. Git commit user name. Defaults to "$GITHUB_ACTOR"
- `wdPath` - **Optional**. To specify a directory other than the repository root to check for changed files.
