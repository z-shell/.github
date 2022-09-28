#!/usr/bin/env bash

set -e

CONFIG_FILE=$(rclone config file | grep 'rclone.conf' | awk '{print $1}')
echo "$CONFIG_FILE"

if [[ -n $RCLONE_CONF ]]; then
  echo "$RCLONE_CONF" >"$CONFIG_FILE"
fi

sh -c "rclone $*"
