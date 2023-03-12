# Notes

## Dispatch

If you want to programmatically trigger updates, you can use the GitHub REST API's repository dispatch events by triggering an event in your repository called setup:

```perl
curl \
  -X POST \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/user/repo/dispatches \
  -d '{ "event_type": "setup" }'
```

Or, with JavaScript (@octokit/core.js):

```js
await octokit.request("POST /repos/{owner}/{repo}/dispatches", {
  owner: "user",
  repo: "repo",
  event_type: "setup",
});
```
