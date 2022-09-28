#!/usr/bin/env bash

set -e

RCLONE_CONF_PATH="${HOME}/.config/rclone"

if [[ -n $RCLONE_CONF ]]; then
  if [[ ! -d $RCLONE_CONF_PATH ]]; then
    mkdir -p "$RCLONE_CONF_PATH"
  fi
  echo "$RCLONE_CONF" >"${RCLONE_CONF_PATH}/rclone.conf"
fi

set -o xtrace
bash -c "rclone $*"
