#!/usr/bin/env bash
# Create the shared Docker bridge networks that are missing.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/ensure-networks.sh NAME:SUBNET [NAME:SUBNET ...]

Create each missing Docker bridge network with its preferred subnet. When the
subnet overlaps another Docker address pool (OrbStack/Docker Desktop), create
the network with an auto-assigned subnet instead.

Example:
  scripts/ensure-networks.sh traefik_proxy:10.0.0.0/16 backend_net:10.1.0.0/16
EOF
}

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  [[ $# -eq 0 ]] && exit 2
  exit 0
fi

for pair in "$@"; do
  if [[ "$pair" != *:* ]]; then
    echo "  ERROR: expected NAME:SUBNET, got '$pair'" >&2
    usage >&2
    exit 2
  fi
  name=${pair%%:*}
  subnet=${pair#*:}
  if docker network inspect "$name" >/dev/null 2>&1; then
    echo "  $name: already exists"
  elif docker network create "$name" --subnet "$subnet" --driver bridge >/dev/null 2>&1; then
    echo "  $name: created ($subnet)"
  elif docker network create "$name" --driver bridge >/dev/null 2>&1; then
    echo "  $name: created (auto subnet; $subnet overlapped another Docker pool)"
  else
    echo "  ERROR: could not create $name" >&2
    exit 1
  fi
done
