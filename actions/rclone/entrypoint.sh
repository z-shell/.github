#!/usr/bin/env bash

# Run rclone for files and directories from different cloud storage providers.
if [[ $DEBUG == "false" ]]; then
  # Carry on, but do quit on errors
  set -e
elif [[ $DEBUG == "true" ]]; then
  # Verbose debugging
  set -exuo pipefail xtrace
  export LOG_LEVEL=debug
  export ACTIONS_STEP_DEBUG=true
fi

if [[ -z $CONFIG_FILE ]]; then
  # Get default location for the configuration file
  CONFIG_FILE=$(rclone config file | grep 'rclone.conf' | awk '{print $1}')
fi

if [[ -n $RCLONE_CONF ]]; then
  # Write user set rclone configuration
  echo "$RCLONE_CONF" >"$CONFIG_FILE"
else
  # Unable to proceed if rclone configuration not set
  echo "The configuration for the rclone is not set"
  exit 1
fi

if [[ ! -x "$(command -v rclone)" ]]; then
  # Unable to proceed as executable rclone not found
  echo 'Failed to install rclone or has non-executable permissions' >&2
  exit 1
fi

run_rclone=$(sh -c "rclone $*")
echo "rclone=$run_rclone" >>"$GITHUB_OUTPUT"
