<!-- GENERATED from knowledge/domains/ci/commit-action.md. Do not edit this delivery copy.
Regenerate: python3 automation/knowledge/knowledge-delivery.py
Check: python3 automation/knowledge/knowledge-delivery.py --check -->

# GitHub Action for Git commit

This Action for git commits any changed files and pushes those changes back to the origin repository.

## Usage

An example workflow to commit and push any changes back to the GitHub origin repository:

```YAML
name: "🆗 Commit"

on: [push]

jobs:
  grunt-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.ref }}
      - run: |
          echo "Something to be commited"
          date > date.txt
      - name: "🆗 Commit"
        uses: z-shell/.github/actions/commit@main
        #  with:
        #    commitMessage: Git Commit Message. Defaults to "Regenerate build artifacts." [Optional]
        #    workDir: To specify a directory other than the repository root to check for changed files [Optional]
        #    commitUserEmail: User email for the commit message [Optional]
        #    commitUserName: User name for the commit message [Optional]
```
