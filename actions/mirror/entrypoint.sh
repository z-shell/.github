#!/bin/sh

set -e

if [ -n "$SSH_PRIVATE_KEY" ]; then
  command mkdir -p /root/.ssh
  echo "$SSH_PRIVATE_KEY" >/root/.ssh/id_rsa
  command chmod 600 /root/.ssh/id_rsa
fi

if [ -n "$SSH_KNOWN_HOSTS" ]; then
  command mkdir -p /root/.ssh
  echo "StrictHostKeyChecking yes" >>/etc/ssh/ssh_config
  echo "$SSH_KNOWN_HOSTS" >/root/.ssh/known_hosts
  command chmod 600 /root/.ssh/known_hosts
else
  echo "WARNING: StrictHostKeyChecking disabled"
  echo "StrictHostKeyChecking no" >>/etc/ssh/ssh_config
fi

command mkdir -p ~/.ssh
command cp /root/.ssh/* ~/.ssh/ 2>/dev/null || true

sh -c "/mirror.sh $*"
