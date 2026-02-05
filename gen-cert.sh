#!/bin/bash

# --- 1. Identify the local IP address ---
# This logic handles differences between macOS (BSD) and Linux (GNU) ifconfig output
# It filters for IPv4, removes the loopback address, and picks the first active interface
CURRENT_IP=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | awk '{print $2}' | sed 's/addr://' | head -n 1)

echo "Local IP detected: $CURRENT_IP"

# --- 2. Ensure the output directory exists ---
mkdir -p traefik/certs

# --- 3. Generate the SSL certificate ---
# Includes the dynamic IP, localhost, and IPv6 loopback in the SAN (Subject Alternative Name)
mkcert -cert-file traefik/certs/server.crt \
       -key-file traefik/certs/server.key \
       "$CURRENT_IP" \
       localhost \
       127.0.0.1 \
       ::1

echo "Success: Certificates are generated in traefik/certs/"
