# Pull-request issue links

Follow the canonical [triage](https://github.com/z-shell/.github/blob/main/runbooks/triage.md) and [pull-request](https://github.com/z-shell/.github/blob/main/runbooks/pull-requests.md) runbooks for authority and disposition. Discover the current tool contract before using these command mechanics.

Closing keywords create a Development link only when the pull request targets the repository's default branch. If repository policy requires a non-default base, preserve that base and create a manual closing reference after explicit authority. Do not retarget the pull request merely to activate the keyword. A manual link does not change GitHub's default-branch requirement for closing the issue.

Prefer a discovered high-level capability. If none exists, confirm the current GraphQL schema exposes `addCloseIssueReferences` with `issueId` and `pullRequestIds`, then use the issue and pull-request node IDs:

```sh
gh api graphql \
  -f query='mutation($issueId: ID!, $pullRequestIds: [ID!]!) { addCloseIssueReferences(input: {issueId: $issueId, pullRequestIds: $pullRequestIds}) { issue { number } } }' \
  -f issueId='ISSUE_NODE_ID' \
  -F 'pullRequestIds[]=PR_NODE_ID'
```

Keep the complete `pullRequestIds[]=...` field quoted in Zsh so `NOMATCH` does not reject it before `gh` runs. Read both `closedByPullRequestsReferences` on the issue and `closingIssuesReferences` on the pull request back after the mutation.

For the current API contract, see GitHub’s [issue mutations](https://docs.github.com/en/graphql/reference/issues#addcloseissuereferences).
