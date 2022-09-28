#!/usr/bin/env bash

if [[ $DEBUG == "false" ]]; then
  # Carry on, but do quit on errors
  set -e
else
  # Verbose debugging
  set -exuo pipefail xtrace
  export LOG_LEVEL=debug
  export ACTIONS_STEP_DEBUG=true
fi

CONFIG_FILE=$(rclone config file | grep 'rclone.conf' | awk '{print $1}')

if [[ -n $RCLONE_CONF ]]; then
  echo "$RCLONE_CONF" >"$CONFIG_FILE"
else
  echo "The configuaration for the rclone is not set"
  exit 1
fi

if [[ ! -x "$(command -v rclone)" ]]; then
  echo 'Error: rclone failed to install or has non-executable permissions' >&2
  exit 1
fi

bash -c "rclone $*"
