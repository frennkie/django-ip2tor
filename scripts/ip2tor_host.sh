#!/usr/bin/env bash
#
# ip2tor_host.sh
#
# License: MIT
# Copyright (c) 2020 The RaspiBlitz developers

# set -e  # doesn't work well with exit 1 from ip2torc.sh

# How to show debug logs:
# DEBUG_LOG=1 ./ip2tor_host.sh

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
  echo "ip2tor_host.sh activate"
  echo "ip2tor_host.sh checkin NUMBER \"MESSAGE\""
  echo "ip2tor_host.sh hello"
  echo "ip2tor_host.sh list [I|P|A|S|H|Z|D|F]"
  echo "ip2tor_host.sh loop"
  echo "ip2tor_host.sh suspend"
  exit 1
fi


###################
# DEBUG + CHECKS
###################
DEBUG_LOG=${DEBUG_LOG:-0}
function debug() { ((DEBUG_LOG)) && echo "### $*"; }

if ! command -v tor >/dev/null; then
  echo "Tor not found - please install it!"
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

if [[ "${IP2TOR_SHOP_URL}" == *".onion" ]]; then
  debug "IP2TOR_SHOP_URL is .onion"
  CURL_TOR="-x socks5h://127.0.0.1:9050/"
  if [[ "${IP2TOR_SHOP_URL}" == "https://"* ]]; then
    echo "Error: IP2TOR_SHOP_URL is .onion but tries HTTPS. Change to HTTP."
    exit 1
  fi
else
  debug "IP2TOR_SHOP_URL is NOT .onion"
  CURL_TOR=""
    if [[ "${IP2TOR_SHOP_URL}" == "http://"* ]]; then
    echo "Error: Change IP2TOR_SHOP_URL to HTTPS"
    exit 1
  fi
fi

if [ ! -f "/usr/local/bin/ip2torc.sh" ]; then
  echo "Error: /usr/local/bin/ip2torc.sh is missing"
  exit 1
fi

IP2TORC_CMD=/usr/local/bin/ip2torc.sh


###################
# FUNCTIONS
###################
function get_tor_bridges() {
  # first parameter to function
  local status=${1-all}

  if [ "${status}" = "all" ]; then
    debug "filter: None"
    local url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/?host=${IP2TOR_HOST_ID}"

  else
    debug "filter: ${status}"
    local url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/?host=${IP2TOR_HOST_ID}&status=${status}"
  fi

  res=$(curl -q ${CURL_TOR} -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" "${url}" 2>/dev/null)

  if [ -z "${res///}" ] || [ "${res///}" = "[]" ]; then
    debug "Nothing to do"
    res=''
  fi

}


#############################
# ACTIVATE (needs activate) #
#############################
if [ "$1" = "activate" ]; then
  get_tor_bridges "P"  # activate (P was pending) - sets ${res}

  detail=$(echo "${res}" | jq -c '.detail' &>/dev/null || true)
  if [ -n "${detail}" ]; then
    echo "${detail}"
    exit 1
  fi

  jsn=$(echo "${res}" | jq -c '.[]|.id,.port,.target | tostring')
  active_list=$(echo "${jsn}" | xargs -L3 | sed 's/ /|/g' | paste -sd "\n" -)

  if [ -z "${active_list}" ]; then
    debug "Nothing to do"
    exit 0
  fi

  echo "ToDo List:"
  echo "${active_list}"
  echo "---"

  for item in ${active_list}; do
    b_id=$(echo "${item}" | cut -d'|' -f1)
    port=$(echo "${item}" | cut -d'|' -f2)
    target=$(echo "${item}" | cut -d'|' -f3)

    DEBUG_LOG=$DEBUG_LOG "${IP2TORC_CMD}" add "${port}" "${target}"

    if [ $? -eq 0 ]; then
      patch_url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/${b_id}/"

      # now send PATCH to ${patch_url} that ${b_id} is done
      res=$(
        curl -X "PATCH" \
        ${CURL_TOR} \
        -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{"status": "A"}' \
        "${patch_url}" 2>/dev/null
      )

      debug "Res: ${res}"
      echo "set to active: ${b_id}"
    fi

  done


############
# CHECK-IN #
############
elif [ "$1" = "checkin" ]; then
  ci_status="$2"
  ci_message="$3"
  url="${IP2TOR_SHOP_URL}/api/v1/hosts/${IP2TOR_HOST_ID}/check_in/"

  res=$(
      curl -q -X "POST" \
      ${CURL_TOR} \
      -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" \
      -H "Content-Type: application/json" \
      --data "{\"ci_status\": \"${ci_status}\", \"ci_message\": \"${ci_message}\"}" \
      "${url}" 2>/dev/null
  )
  debug "${res}"


#########
# HELLO #
#########
elif [ "$1" = "hello" ]; then
  url="${IP2TOR_SHOP_URL}/api/v1/hosts/${IP2TOR_HOST_ID}/check_in/"
  res=$(curl -q ${CURL_TOR} -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" "${url}" 2>/dev/null)
  debug "${res}"


########
# LIST #
########
elif [ "$1" = "list" ]; then
  get_tor_bridges "${2-all}"

  if [ -z "${res}" ]; then
    debug "Nothing"
    exit 0
  else
    jsn=$(echo "${res}" | jq -c '.[]|.port,.id,.status,.target | tostring')
    active_list=$(echo "${jsn}" | xargs -L4 | sed 's/ /|/g' | paste -sd "\n" -)
    echo "${active_list}" | sort -n
  fi

########
# LOOP #
########
elif [ "$1" = "loop" ]; then
  echo "Running on Shop: ${IP2TOR_SHOP_URL} (Host ID: ${IP2TOR_HOST_ID})"
  while :
  do
    "${0}" activate
    "${0}" suspend
    "${0}" hello
    sleep 2
  done

#################
# NEEDS_SUSPEND #
#################
elif [ "$1" = "suspend" ]; then
  get_tor_bridges "S"  # S for (needs) suspend - update to "H" (suspended/hold) - sets ${res}

  detail=$(echo "${res}" | jq -c '.detail' &>/dev/null || true)
  if [ -n "${detail}" ]; then
    echo "${detail}"
    exit 1
  fi

  jsn=$(echo "${res}" | jq -c '.[]|.id,.port,.target | tostring')
  suspend_list=$(echo "${jsn}" | xargs -L3 | sed 's/ /|/g' | paste -sd "\n" -)

  if [ -z "${suspend_list}" ]; then
    # echo "DEBUG: Nothing to do"
    exit 0
  fi

  echo "ToDo List:"
  echo "${suspend_list}"
  echo "---"

  for item in ${suspend_list}; do
    b_id=$(echo "${item}" | cut -d'|' -f1)
    port=$(echo "${item}" | cut -d'|' -f2)
    target=$(echo "${item}" | cut -d'|' -f3)

    DEBUG_LOG=$DEBUG_LOG "${IP2TORC_CMD}" remove "${port}"

    if [ $? -eq 0 ]; then
      patch_url="${IP2TOR_SHOP_URL}/api/v1/tor_bridges/${b_id}/"

      # now send PATCH to ${patch_url} that ${b_id} is done
      res=$(
        curl -X "PATCH" \
        ${CURL_TOR} \
        -H "Authorization: Token ${IP2TOR_HOST_TOKEN}" \
        -H "Content-Type: application/json" \
        --data '{"status": "H"}' \
        "${patch_url}" 2>/dev/null
      )

      debug "Res: ${res}"
      echo "set to suspended (hold): ${b_id}"
    fi

  done

else
  echo "unknown command - run with -h for help"
  exit 1
fi
