#!/usr/bin/env bash

IP2TOR_CONFIG_FILE="/etc/ip2tor.conf"
TELEGRAF_CONFIG="/etc/telegraf/telegraf.d/ip2tor_tor_bridges_all.conf"
TMP_FILE="/tmp/ip2tor_tor_bridges_all.conf"

# How to show debug logs:
# DEBUG_LOG=1 ./telegraf_ip2tor_update_.sh
DEBUG_LOG=${DEBUG_LOG:-0}
function debug() { ((DEBUG_LOG)) && echo "### $*"; }

# check if running as root
if [ "${EUID}" != "0" ]; then
    echo "please run as root"
    exit 1
fi

# check for and source config
if [ -f "${IP2TOR_CONFIG_FILE}" ]; then
    source "${IP2TOR_CONFIG_FILE}"
else
    echo "missing config: ${IP2TOR_CONFIG_FILE}"
    exit 1
fi

debug "trying to get currrent config (via Tor) and storing in: \"${TMP_FILE}\"..."
if ! curl -s -X GET -x "socks5h://127.0.0.1:9050/" -H "Authorization: Token ${IP2TOR_TELEGRAF_TOKEN}" -o ${TMP_FILE} "${IP2TOR_SHOP_URL}/api/v1/tor_bridges/get_telegraf_config/"; then
    debug "cURL error"
    rm -rf "${TMP_FILE}"
    exit 1
fi

debug "checking for changes..."
if [ ! -f ${TELEGRAF_CONFIG} ]; then
    echo "missing telegraf config: ${TELEGRAF_CONFIG} (consider using: ${TMP_FILE})"
    exit 1
fi

if ! diff -q ${TELEGRAF_CONFIG} ${TMP_FILE} >/dev/null 2>&1; then
    debug "files DO NOT match"
    cp -f ${TMP_FILE} ${TELEGRAF_CONFIG}
    rm -rf "${TMP_FILE}"

    debug "checking new config..."
    if ! telegraf --test >/dev/null 2>&1; then
        debug "config error"
    else
        debug "config OK - restarting service..."
        systemctl restart telegraf
    fi
else
    debug "files match - no changes needed!"
    rm -rf "${TMP_FILE}"
    exit 0
fi

# EOF
