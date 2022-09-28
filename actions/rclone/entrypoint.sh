#!/usr/bin/env bash

set -e

if [[ -n $RCLONE_CONF ]]; then
  if [[ ! -d $RCLONE_CONF_PATH ]]; then
    mkdir -p "$RCLONE_CONF_PATH"
  fi
  echo "$RCLONE_CONF" >"${RCLONE_CONF_PATH}/rclone.conf"
else
  echo "Set the RCLONE_CONF env variable."
  exit 1
fi

set -o xtrace
bash -c "rclone $RUN"
