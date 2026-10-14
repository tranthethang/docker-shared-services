#!/usr/bin/env bash
# Remove every container and volume of the combined Compose project after confirmation.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/remove-all.sh -f COMPOSE_FILE [-f COMPOSE_FILE ...]

Ask for confirmation, then run `docker compose <args> down -v`. This deletes
the data volumes of every listed Compose file.
EOF
}

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  [[ $# -eq 0 ]] && exit 2
  exit 0
fi

echo "⚠️  WARNING: This will remove all data from all services!"
REPLY=""
read -p "Are you sure? (y/n) " -n 1 -r || true
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  docker compose "$@" down -v
  echo "✅ All containers and volumes removed"
else
  echo "Operation cancelled"
fi
