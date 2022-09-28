#!/usr/bin/env bash

set -e

RCLONE_CONF_PATH="${HOME}/.config/rclone"

if [[ -z $GITHUB_TOKEN ]]; then
  echo "Set the GITHUB_TOKEN env variable."
  exit 1
fi

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
bash -c "rclone $*"
