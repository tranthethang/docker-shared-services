#!/usr/bin/env bash
# Generate the Traefik TLS certificate with mkcert.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/gen-certs.sh CERT_DIR

Write CERT_DIR/server.crt and CERT_DIR/server.key with mkcert. The certificate
covers the first non-loopback local IP, *.dss.localhost and its nested
wildcards, localhost, 127.0.0.1, and ::1.
EOF
}

if [[ $# -ne 1 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  [[ $# -eq 1 ]] && exit 0
  exit 2
fi

cert_dir=$1

echo "Detecting local IP..."
current_ip=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $2}' | sed 's/addr://' | head -n 1 || true)
echo "Local IP detected: $current_ip"
mkdir -p "$cert_dir"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "❌ Error: mkcert is not installed. Please install it first."
  exit 1
fi

mkcert -cert-file "$cert_dir/server.crt" \
  -key-file "$cert_dir/server.key" \
  "$current_ip" \
  "*.dss.localhost" \
  "*.minio.dss.localhost" \
  "*.garage.dss.localhost" \
  "*.tts.dss.localhost" \
  "dss.localhost" \
  localhost \
  127.0.0.1 \
  ::1
echo "✅ Success: Certificates are generated in $cert_dir/"
