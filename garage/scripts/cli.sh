#!/usr/bin/env bash
# Thin host-side wrapper: `./scripts/cli.sh bucket list`
# Prefer this over raw `docker exec` only if you need the reminder; after the
# directory-mount fix, `docker exec garage /garage …` works the same way.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! docker container inspect garage >/dev/null 2>&1; then
  echo "error: container 'garage' is not running. From this directory: docker compose up -d" >&2
  exit 1
fi

exec docker exec garage /garage "$@"
