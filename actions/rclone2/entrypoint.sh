#!/usr/bin/env bash

set -e

if [[ -n $RCLONE_CONF_PATH ]]; then
  if [[ -d $RCLONE_CONF_PATH ]]; then
    echo "Set directory: $RCLONE_CONF_PATH"
  else
    mkdir -p "$RCLONE_CONF_PATH"
  fi
else
  echo "The RCLONE_CONF_PATH environment variable is empty"
  exit 1
fi

if [[ -n $RCLONE_CONF ]]; then
  echo "$RCLONE_CONF" >"$RCLONE_CONF_PATH/rclone.conf"
else
  echo "The RCLONE_CONF environment variable is empty"
  exit 1
fi

bash -c "rclone $*"
#else
#  echo "The RUN environment variable is empty"
#  exit 1
#fi
