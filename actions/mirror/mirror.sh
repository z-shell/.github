#!/bin/sh

set -e

SOURCE_REPO=$1
DESTINATION_REPO=$2
SOURCE_DIR=$(basename "$SOURCE_REPO")
DRY_RUN=$3

GIT_SSH_COMMAND="ssh -v"

echo "GIT_SSH_COMMAND=$GIT_SSH_COMMAND"
echo "SOURCE=$SOURCE_REPO"
echo "DESTINATION=$DESTINATION_REPO"
echo "DRY RUN=$DRY_RUN"

command git clone --mirror "$SOURCE_REPO" "$SOURCE_DIR" && cd "$SOURCE_DIR" || true
command git remote set-url --push origin "$DESTINATION_REPO"
command git fetch -p origin
command git for-each-ref --format 'delete %(refname)' refs/pull | git update-ref --stdin

if [ "$DRY_RUN" = "true" ]; then
  echo "[Info]: Dry Run, no data is pushed"
  command git push --mirror --dry-run
else
  command git push --mirror
fi
