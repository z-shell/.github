#!/usr/bin/env bash

set -e

CONFIG_FILE=$(sh -c "rclone config file | grep 'rclone.conf' | awk '{print $1}'")

if [[ -n $RCLONE_CONF ]]; then
  echo "$RCLONE_CONF" >"$CONFIG_FILE"
fi

sh -c "rclone $*"
