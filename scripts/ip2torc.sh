#!/usr/bin/env bash
#
# ip2torc.sh
#
# License: MIT
# Copyright (c) 2020 The RaspiBlitz developers

set -u

# How to show debug logs:
# DEBUG_LOG=1 ./ip2torc.sh

# command info
if [ $# -eq 0 ] || [ "$1" = "-h" ] || [ "$1" = "-help" ] || [ "$1" = "--help" ]; then
  echo "management script to add, check, list or remove IP2Tor bridges (using socat and systemd)"
  echo "ip2torc.sh add [PORT] [TARGET]"
  echo "ip2torc.sh check [TARGET]"
  echo "ip2torc.sh list"
  echo "ip2torc.sh remove [PORT]"
  exit 1
fi


###################
# DEBUG + CHECKS
###################
DEBUG_LOG=${DEBUG_LOG:-0}
function debug() { ((DEBUG_LOG)) && echo "### $*"; }

if ! command -v tor >/dev/null; then
  echo "Tor is not installed - exiting."
  echo "Please setup Tor and run again."
  exit 1
fi

if ! command -v socat >/dev/null; then
  echo "socat not found - installing it now..."
  sudo apt-get update &>/dev/null
  sudo apt-get install -y socat &>/dev/null
  echo "socat installed successfully."
fi


###################
# FUNCTIONS
###################
function add_bridge() {
  # requires sudo
  port=${1}
  target=${2}
  echo "adding bridge from port: ${port} to: ${target}"

  file_path="/etc/systemd/system/ip2tor_${port}.service"
  if [ -f "${file_path}" ]; then
    debug "file exists already"
    exit 0
  fi

  if getent passwd debian-tor > /dev/null 2&>1 ; then
    service_user=debian-tor
  elif getent passwd toranon > /dev/null 2&>1 ; then
    service_user=toranon
  else
    service_user=root
  fi

  cat <<EOF | sudo tee "${file_path}" >/dev/null
[Unit]
Description=IP2Tor Tunnel Service (Port ${port})
After=network.target

[Service]
User=${service_user}
Group=${service_user}
ExecStart=/usr/bin/socat TCP4-LISTEN:${port},bind=0.0.0.0,reuseaddr,fork SOCKS4A:localhost:${target},socksport=9050
StandardOutput=journal

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl enable ip2tor_"${port}"
  sudo systemctl start ip2tor_"${port}"

}

function check_bridge_target() {
  target=${1}
  echo "checking bridge target: ${target}"
  echo "no idea yet what and how to check!"
}

function list_bridges() {
  echo "# Bridges (PORT|TARGET|STATUS)"
  echo "# ============================"

  for f in /etc/systemd/system/ip2tor_*.service; do
    [ -e "$f" ] || continue

    cfg=$(sed -n 's/^ExecStart.*TCP4-LISTEN:\([0-9]*\),.*SOCKS4A:localhost:\(.*\),socksport=.*$/\1|\2/p' "${f}")
    port=$(echo "${cfg}" | cut -d"|" -f1)
    target=$(echo "${cfg}" | cut -d"|" -f2)
    status=$(systemctl status "ip2tor_${port}.service" | grep "Active" | sed 's/^ *Active: //g')
    echo "${port}|${target}|${status}"
  done

}

function remove_bridge() {
  # requires sudo
  port=${1}
  echo "removing bridge from port: ${port}"

  file_path="/etc/systemd/system/ip2tor_${port}.service"
  if ! [ -f "${file_path}" ]; then
    echo "file does not exist"
    echo "no bridge on this port..!"
    exit 1
  fi

  echo "will now stop, disable and remove service and then refresh systemd"
  sudo systemctl stop ip2tor_"${port}"
  sudo systemctl disable ip2tor_"${port}"
  sudo rm -rf "${file_path}"
  sudo systemctl daemon-reload
  sudo systemctl reset-failed ip2tor_"${port}"
  echo "successfully stopped and removed bridge."

}

#######
# ADD #
#######
if [ "$1" = "add" ]; then
  if ! [ $# -eq 3 ]; then
    echo "wrong number of arguments - run with -h for help"
    exit 1
  fi
  add_bridge "${2}" "${3}"

#########
# CHECK #
#########
elif [ "$1" = "check" ]; then
  if ! [ $# -eq 2 ]; then
    echo "wrong number of arguments - run with -h for help"
    exit 1
  fi
  check_bridge_target "${2}"

########
# LIST #
########
elif [ "$1" = "list" ]; then
  if ! [ $# -eq 1 ]; then
    echo "wrong number of arguments - run with -h for help"
    exit 1
  fi
  list_bridges

##########
# REMOVE #
##########
elif [ "$1" = "remove" ]; then
  if ! [ $# -eq 2 ]; then
    echo "wrong number of arguments - run with -h for help"
    exit 1
  fi
  remove_bridge "${2}"

else
  echo "unknown command - run with -h for help"
  exit 1
fi
