#!/usr/bin/env bash
# Apply POSTGRES_PASSWORD on every start, including an existing data directory.
# The official image sets that password only while the directory is empty, so a
# later .env change leaves scram auth rejecting clients and those clients restart.
set -euo pipefail

PGDATA="${PGDATA:-/var/lib/postgresql/data}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"

sync_role_password() {
  local attempt
  for attempt in $(seq 1 60); do
    if pg_isready -q -U "${POSTGRES_USER}"; then
      psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres \
        --set=role="${POSTGRES_USER}" --set=pw="${POSTGRES_PASSWORD}" <<'SQL'
ALTER USER :"role" WITH PASSWORD :'pw';
SQL
      echo "postgres: aligned role '${POSTGRES_USER}' with POSTGRES_PASSWORD"
      return 0
    fi
    if [[ "${attempt}" -eq 60 ]]; then
      echo "postgres: timed out aligning the role password" >&2
      return 1
    fi
    sleep 1
  done
}

stop_child() {
  if [[ -n "${child:-}" ]]; then
    kill -TERM "${child}" 2>/dev/null || true
    wait "${child}" || true
  fi
}

if [[ -s "${PGDATA}/PG_VERSION" && -n "${POSTGRES_PASSWORD:-}" ]]; then
  docker-entrypoint.sh postgres &
  child=$!
  trap stop_child TERM INT
  if ! sync_role_password; then
    stop_child
    exit 1
  fi
  wait "${child}"
else
  exec docker-entrypoint.sh postgres
fi
