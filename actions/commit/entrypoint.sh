#!/usr/bin/env sh
# This GitHub Action for git commits any changed files and pushes
# those changes back to the origin repository.
#
# Required environment variable:
# - $GITHUB_TOKEN: The token to use for authentication with GitHub
# to commit and push changes back to the origin repository.
#
# Optional environment variables:
# - $WD_PATH: Working directory to CD into before checking for changes
# - $PUSH_BRANCH: Remote branch to push changes to
# - $COMMIT_EMAIL and $COMMIT_NAME: The email and user name to use for the commit author.

if [ "$DEBUG" = "false" ]; then
  # Carry on, but do quit on errors
  set -e
else
  # Verbose debugging
  # set -exuo pipefail
  export LOG_LEVEL=debug
  export ACTIONS_STEP_DEBUG=true
fi

# If WD_PATH is defined, then cd to it
if [ -n "$WD_PATH" ]; then
  echo "Changing dir to $WD_PATH"
  cd "$WD_PATH"
fi

# Set up .netrc file with GitHub credentials
git_setup() {
  # If commit email and user name variables not set then use $GITHUB_ACTOR.
  #	(The name of the person or app that initiated the workflow)
  if [ -z "$COMMIT_EMAIL" ] && [ -z "$COMMIT_EMAIL" ]; then
    git config user.email "$GITHUB_ACTOR@users.noreply.github.com"
    git config user.name "$GITHUB_ACTOR"
  else
    git config user.email "$COMMIT_EMAIL"
    git config user.name "$COMMIT_USER"
  fi
}

# This section only runs if there have been file changes
echo "Checking for uncommitted changes in the git working tree."
if expr "$(git status --porcelain | wc -l)" \> 0; then
  git_setup
  git add .
  git commit -m "$COMMIT_MESSAGE"
  git push
else
  echo "Working tree clean. Nothing to commit."
fi
