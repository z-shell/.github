#!/usr/bin/env bash

set -e

if [[ -n $RCLONE_CONF ]]; then
  [[ -d $RCLONE_CONF_PATH ]] || mkdir -p "$RCLONE_CONF_PATH"
  echo "$RCLONE_CONF" >"${RCLONE_CONF_PATH}/rclone.conf"
else
  echo "The RCLONE_CONF environment variable is empty"
  exit 1
fi

sh -c "rclone $RUN"
