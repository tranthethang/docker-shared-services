#!/usr/bin/env bash
# Generate the Dozzle users file from the shared password when it is missing.
set -euo pipefail

LEGACY_PASSWORD='Password102!'

usage() {
  cat <<'EOF'
Usage: scripts/ensure-dozzle-users.sh USERS_FILE [ROOT_ENV_FILE]

Write an admin entry to USERS_FILE (for example dozzle/data/users.yml) unless it
already exists. A directory at USERS_FILE is removed and regenerated. The
password comes from $DSS_SHARED_PASSWORD, else from DSS_SHARED_PASSWORD in
ROOT_ENV_FILE (default: .env). The legacy placeholder password is rejected.
EOF
}

if [[ $# -lt 1 || $# -gt 2 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  [[ $# -ge 1 && ("$1" == "-h" || "$1" == "--help") ]] && exit 0
  exit 2
fi

users_file=$1
env_file=${2:-.env}

mkdir -p "$(dirname "$users_file")"
if [[ -d "$users_file" ]]; then
  echo "  $users_file is a directory -> removing and regenerating..."
  rm -rf "$users_file"
fi

if [[ -f "$users_file" ]]; then
  echo "  $users_file already exists"
  exit 0
fi

password="${DSS_SHARED_PASSWORD:-}"
if [[ -z "$password" && -f "$env_file" ]]; then
  password=$(grep -E '^DSS_SHARED_PASSWORD=' "$env_file" | head -1 | cut -d= -f2- || true)
fi
if [[ -z "$password" || "$password" == "$LEGACY_PASSWORD" ]]; then
  echo "  ERROR: DSS_SHARED_PASSWORD is missing or still $LEGACY_PASSWORD. Run make setup before generating Dozzle users." >&2
  exit 1
fi

echo "  $users_file not found -> generating admin (shared password)..."
docker run --rm -i amir20/dozzle generate admin \
  --password "$password" \
  --email admin@example.com \
  --name "Admin" >"$users_file"
