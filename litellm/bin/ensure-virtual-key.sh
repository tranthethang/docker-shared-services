#!/bin/sh
set -eu

# Wait for the proxy, then store LITELLM_VIRTUAL_KEY. Do not print either key.
i=0
while [ "$i" -lt 60 ]; do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
    http://litellm:4000/health/liveliness || true)
  if [ "$code" = "200" ]; then
    break
  fi
  i=$((i + 1))
  sleep 2
done

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
  http://litellm:4000/health/liveliness || true)
if [ "$code" != "200" ]; then
  echo "litellm health check did not return 200" >&2
  exit 1
fi

umask 077
cfg=$(mktemp)
body=$(mktemp)
out=$(mktemp)
trap 'rm -f "$cfg" "$body" "$out"' EXIT

virtual=$(printf '%s' "$LITELLM_VIRTUAL_KEY" | sed 's/\\/\\\\/g; s/"/\\"/g')
master=$(printf '%s' "$LITELLM_MASTER_KEY" | sed 's/\\/\\\\/g; s/"/\\"/g')
printf '{"key":"%s","models":[]}' "$virtual" > "$body"
cat > "$cfg" <<EOF
silent
show-error
request = POST
url = "http://litellm:4000/key/generate"
header = "Authorization: Bearer ${master}"
header = "Content-Type: application/json"
data-binary = "@${body}"
output = "${out}"
write-out = "%{http_code}"
max-time = 30
EOF

code=$(curl --config "$cfg" || true)
if [ "$code" = "200" ] || grep -qi 'already exists' "$out"; then
  echo "virtual key stored"
  exit 0
fi
echo "key generate failed" >&2
exit 1
