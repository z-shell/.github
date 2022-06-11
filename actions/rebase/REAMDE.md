# GitHub Action Rebase

To configure the action simply add the following lines to your `.github/workflows/rebase.yml` workflow file:

```YAML
name: "🔁 Rebase"
on:
  issue_comment:
    types: [created]
jobs:
  rebase:
    name: 🔁 Rebase
    if: >-
      github.event.issue.pull_request != '' && 
      (
        contains(github.event.comment.body, '/rebase') || 
        contains(github.event.comment.body, '/autosquash')
      )
    steps:
      - name: Checkout the latest code
        uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          fetch-depth: 0 # otherwise, you will fail to push refs to dest repo
      - name: 🔁 Rebase
        uses: z-shell/.github/actions/rebase@main
        with:
          autosquash: ${{ contains(github.event.comment.body, '/autosquash') || contains(github.event.comment.body, '/rebase-autosquash') }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

:exclamation: To ensure GitHub Actions is automatically re-run after a successful rebase action use a [Personal Access Token](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token):

```YAML
    - name: Checkout the latest code
      uses: actions/checkout@v3
      with:
        token: ${{ secrets.GH_PAT }}
        fetch-depth: 0 # otherwise, you will fail to push refs to dest repo
    - name: 🔁 Rebase
      uses: z-shell/.github/actions/rebase@main
      env:
        GITHUB_TOKEN: ${{ secrets.GH_PAT }}
```

You can also optionally specify the PR number of the branch to rebase, if the action you're running doesn't directly refer to a specific pull request:

```YAML
    - name: 🔁 Rebase
      uses:  z-shell/.github/actions/rebase@main
      env:
        GITHUB_TOKEN: ${{ secrets.PAT_TOKEN }}
        PR_NUMBER: 12
```


## Restricting who can call the action

It's possible to use `author_association` field of a comment to restrict who can call the action and skip the rebase for others. Simply add the following expression to the `if` statement in your workflow file: `github.event.comment.author_association == 'MEMBER'`. See [documentation](https://developer.github.com/v4/enum/commentauthorassociation/) for a list of all available values of `author_association`.

> GitHub can also optionally dismiss an existing review automatically after rebase, so you'll need to re-approve again which will trigger the test workflow.
Set it up in your repository *Settings* > *Branches* > *Branch protection rules* > *Require pull request reviews before merging* > *Dismiss stale pull request approvals when new commits are pushed*.
