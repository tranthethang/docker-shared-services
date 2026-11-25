#!/bin/sh
set -eu

# Wait for the proxy, then store LITELLM_VIRTUAL_KEY. Do not print either key.
i=0
while [ "$i" -lt 60 ]; do
  if python3 -c 'import sys, urllib.request
try:
    status = urllib.request.urlopen("http://litellm:4000/health/liveliness", timeout=5).status
except Exception:
    sys.exit(1)
sys.exit(0 if status == 200 else 1)'; then
    break
  fi
  i=$((i + 1))
  sleep 2
done

python3 -c 'import json, os, sys, urllib.error, urllib.request
try:
    status = urllib.request.urlopen("http://litellm:4000/health/liveliness", timeout=5).status
except Exception:
    status = 0
if status != 200:
    sys.exit(1)' || {
  echo "litellm health check did not return 200" >&2
  exit 1
}

python3 -c 'import json, os, sys, urllib.error, urllib.request
master = os.environ["LITELLM_MASTER_KEY"]
virtual = os.environ["LITELLM_VIRTUAL_KEY"]
body = json.dumps({"key": virtual, "models": []}).encode()
req = urllib.request.Request(
    "http://litellm:4000/key/generate",
    data=body,
    headers={"Authorization": "Bearer " + master, "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        status, payload = resp.status, resp.read().decode("utf-8", "replace")
except urllib.error.HTTPError as exc:
    status, payload = exc.code, exc.read().decode("utf-8", "replace")
ok = status == 200 or "already exists" in payload.lower()
sys.exit(0 if ok else 1)' || {
  echo "key generate failed" >&2
  exit 1
}

echo "virtual key stored"
