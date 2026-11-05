#!/usr/bin/env bash
# Remove every container and volume of the combined Compose project after confirmation.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/remove-all.sh

Ask for confirmation, then run `docker compose down -v` for each service stack
(with root and service .env files), removing every data volume.
EOF
}

if [[ $# -gt 0 ]]; then
  if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    usage
    exit 0
  fi
  echo "remove-all.sh takes no arguments (use: make remove-all)" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
UV="${UV:-uv}"
PY=("$UV" run --frozen --no-dev python -m dss.cli.teardown)

echo "⚠️  WARNING: This will remove all data from all services!"
REPLY=""
read -p "Are you sure? (y/n) " -n 1 -r || true
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  "${PY[@]}"
  echo "✅ All containers and volumes removed"
else
  echo "Operation cancelled"
fi
