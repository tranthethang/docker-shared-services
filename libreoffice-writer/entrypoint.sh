#!/usr/bin/env bash
# Run the soffice UNO listener in the foreground and restart it when it exits.
# UNO has no authentication: keep the port on internal networks / localhost only.
set -euo pipefail

UNO_HOST="${UNO_HOST:-0.0.0.0}"
UNO_PORT="${UNO_PORT:-2002}"

child=""

stop_child() {
  if [[ -n "${child}" ]]; then
    kill "${child}" 2>/dev/null || true
  fi
  exit 0
}
trap stop_child TERM INT

while true; do
  soffice --headless --invisible --norestore --nologo --nodefault \
    -env:UserInstallation=file:///tmp/lo_profile \
    --accept="socket,host=${UNO_HOST},port=${UNO_PORT};urp;" &
  child=$!
  wait "${child}" || true
  echo "soffice exited; restarting in 1s" >&2
  sleep 1
done
