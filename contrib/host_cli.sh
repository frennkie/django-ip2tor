#!/usr/bin/env bash
#
# host_cli.sh
#
# License: MIT
# Copyright (c) 2020 The RaspiBlitz developers

set -e
set -u

SHOP_URL="https://shop.ip2t.org"
HOST_ID="<redacted>"
HOST_TOKEN="<redacted>>"  # keep this secret!

TOR2IPC_CMD="./tor2ipc.sh"

# command info
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "-help" ] || [ "$1" = "--help" ]; then
  echo "management script to fetch and process config from shop"
  echo "host_cli.sh pending"
  echo "host_cli.sh list"
  echo "host_cli.sh suspended"
  exit 1
fi

if ! command -v jq >/dev/null; then
  echo "jq not found - installing it now..."
  sudo apt-get update &>/dev/null
  sudo apt-get install -y jq &>/dev/null
  echo "jq installed successfully."
fi

###########
# PENDING #
###########
if [ "$1" = "pending" ]; then

  status="P" # P for pending
  url="${SHOP_URL}/api/tor_bridges/?host=${HOST_ID}&status=${status}"

  res=$(curl -s -q -H "Authorization: Token ${HOST_TOKEN}" "${url}")
  active_list=$(echo "${res}" | jq -c '.[]|.port,.target' | paste - - | sed 's/"//g' | sed 's/\t/|/g')

  if [ -z "${active_list}" ]; then
    echo "Nothing to do"
    exit 0
  fi

  echo "ToDo List:"
  echo "${active_list}"
  echo "---"

  for item in ${active_list}; do
    port=$(echo "${item}" | cut -d'|' -f1)
    target=$(echo "${item}" | cut -d'|' -f2)
    res=$("${TOR2IPC_CMD}" add "${port}" "${target}")
    echo "Status Code: $?"
    echo "${res}"
  done


########
# LIST #
########
elif [ "$1" = "list" ]; then
  echo "list"

#############
# SUSPENDED #
#############
elif [ "$1" = "suspended" ]; then
  echo "suspended"

else
  echo "unknown command - run with -h for help"
  exit 1
fi
