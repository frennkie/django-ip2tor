#!/usr/bin/env bash
#
# ip2tor_host.sh
#
# License: MIT
# Copyright (c) 2020 The RaspiBlitz developers

set -e

# CONFIGURATION: use either environment or file
# ENV:
# export IP2TOR_SHOP_URL=https://ip2tor.fulmo.org
# export IP2TOR_HOST_ID=1234abcd
# export IP2TOR_HOST_TOKEN=abcd4321
# FILE: /etc/ip2tor.conf with content
# IP2TOR_SHOP_URL=https://ip2tor.fulmo.org
# IP2TOR_HOST_ID=1234abcd
# IP2TOR_HOST_TOKEN=abcd4321

# command info
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "-help" ] || [ "$1" = "--help" ]; then
  echo "management script to fetch and process config from shop"
  echo "host_cli.sh pending"
  echo "host_cli.sh list [I|P|A|S|D]"
  echo "host_cli.sh suspended"
  exit 1
fi

if ! command -v jq >/dev/null; then
  echo "jq not found - installing it now..."
  sudo apt-get update &>/dev/null
  sudo apt-get install -y jq &>/dev/null
  echo "jq installed successfully."
fi

###################
# GET CONFIG
###################

if [ -f "/etc/ip2tor.conf" ]; then
  unset IP2TOR_SHOP_URL
  unset IP2TOR_HOST_ID
  unset IP2TOR_HOST_TOKEN

  source "/etc/ip2tor.conf"
fi

if [ -z "${IP2TOR_SHOP_URL}" ] || [ -z "${IP2TOR_HOST_ID}" ] || [ -z "${IP2TOR_HOST_TOKEN}" ]; then
  echo "Error: IP2TOR_SHOP_URL, IP2TOR_HOST_ID and IP2TOR_HOST_TOKEN must be set via environment or config file!"
  exit 1
fi

if [ ! -f "/usr/local/bin/ip2torc.sh" ]; then
  echo "Error: /usr/local/bin/ip2torc.sh is missing"
  exit 1
fi

###################
# FUNCTIONS
###################
function get_tor_bridges() {
  # first parameter to function
  local status=${1-all}

  if [ "${status}" = "all" ]; then
    #echo "filter: None"
    local url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/?host=${IP2TOR_HOST_ID}"

  else
    #echo "filter: ${status}"
    local url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/?host=${IP2TOR_HOST_ID}&status=${status}"
  fi

  res=$(curl -s -q -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" "${url}")

  if [ -z "${res///}" ] || [ "${res///}" = "[]" ]; then
    #echo "Nothing to do"
    res=''
  fi

}


###########
# PENDING #
###########
if [ "$1" = "pending" ]; then
  get_tor_bridges "P"  # P for pending - sets ${res}

  detail=$(echo "${res}" | jq -c '.detail' &>/dev/null || true)
  if [ -n "${detail}" ]; then
    echo "${detail}"
    exit 1
  fi

  jsn=$(echo "${res}" | jq -c '.[]|.id,.port,.target | tostring')
  active_list=$(echo "${jsn}" | xargs -L3 | sed 's/ /|/g' | paste -sd "\n" -)

  if [ -z "${active_list}" ]; then
    echo "Nothing to do"
    exit 0
  fi

  echo "ToDo List:"
  echo "${active_list}"
  echo "---"

  for item in ${active_list}; do
    #echo "Item: ${item}"
    b_id=$(echo "${item}" | cut -d'|' -f1)
    port=$(echo "${item}" | cut -d'|' -f2)
    target=$(echo "${item}" | cut -d'|' -f3)
    #echo "${b_id}"
    #echo "${port}"
    #echo "${target}"

    res=$("${IP2TORC_CMD}" add "${port}" "${target}")
    #echo "Status Code: $?"
    #echo "${res}"

    if [ $? -eq 0 ]; then
      patch_url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/${b_id}/"

      #echo "now send PATCH to ${patch_url} that ${b_id} is done"

      res=$(
        curl -X "PATCH" \
        -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{"status": "A"}' \
        "${patch_url}"
      )

      #echo "Res: ${res}"
      echo "set to active: ${b_id}"
    fi

  done


########
# LIST #
########
elif [ "$1" = "list" ]; then
  get_tor_bridges "${2-all}"

  if [ -z "${res}" ]; then
    echo "Nothing"
    exit 0
  else
    jsn=$(echo "${res}" | jq -c '.[]|.port,.id,.status,.target | tostring')
    active_list=$(echo "${jsn}" | xargs -L4 | sed 's/ /|/g' | paste -sd "\n" -)
    echo "${active_list}" | sort -n
  fi


#############
# SUSPENDED #
#############
elif [ "$1" = "suspended" ]; then
  get_tor_bridges "S"  # S for suspended - sets ${res}

  detail=$(echo "${res}" | jq -c '.detail' &>/dev/null || true)
  if [ -n "${detail}" ]; then
    echo "${detail}"
    exit 1
  fi

  jsn=$(echo "${res}" | jq -c '.[]|.id,.port,.target | tostring')
  suspended_list=$(echo "${jsn}" | xargs -L3 | sed 's/ /|/g' | paste -sd "\n" -)

  if [ -z "${suspended_list}" ]; then
    echo "Nothing to do"
    exit 0
  fi

  echo "ToDo List:"
  echo "${suspended_list}"
  echo "---"

  for item in ${suspended_list}; do
    echo "Item: ${item}"
    b_id=$(echo "${item}" | cut -d'|' -f1)
    port=$(echo "${item}" | cut -d'|' -f2)
    target=$(echo "${item}" | cut -d'|' -f3)
    #echo "${b_id}"
    #echo "${port}"
    #echo "${target}"

    set -x
    res=$("${IP2TORC_CMD}" remove "${port}")
    echo "Status Code: $?"
    echo "${res}"

    if [ $? -eq 0 ]; then
      patch_url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/${b_id}/"

      echo "now send PATCH to ${patch_url} that ${b_id} is done"

      res=$(
        curl -X "PATCH" \
        -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{"status": "D"}' \
        "${patch_url}"
      )

      #echo "Res: ${res}"
      echo "set to deleted: ${b_id}"
    fi

  done

else
  echo "unknown command - run with -h for help"
  exit 1
fi
