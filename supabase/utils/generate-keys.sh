#!/bin/sh
#
# Generate secrets and legacy HS256 JWT API keys for the minimal stack.
#
# Usage:
#   sh generate-keys.sh              # Interactive: print keys, prompt to update .env
#   sh generate-keys.sh --update-env # Print keys and write them to .env
#

set -e

gen_hex() {
    openssl rand -hex "$1"
}

gen_base64() {
    openssl rand -base64 "$1"
}

base64_url_encode() {
    openssl enc -base64 -A | tr '+/' '-_' | tr -d '='
}

gen_token() {
    payload=$1
    payload_base64=$(printf %s "$payload" | base64_url_encode)
    header_base64=$(printf %s "$header" | base64_url_encode)
    signed_content="${header_base64}.${payload_base64}"
    signature=$(printf %s "$signed_content" | openssl dgst -binary -sha256 -hmac "$jwt_secret" | base64_url_encode)
    printf '%s' "${signed_content}.${signature}"
}

if ! command -v openssl >/dev/null 2>&1; then
    echo "Error: openssl is required but not found."
    exit 1
fi

jwt_secret="$(gen_base64 30)"

header='{"alg":"HS256","typ":"JWT"}'
iat=$(date +%s)
exp=$((iat + 5 * 3600 * 24 * 365)) # 5 years

anon_payload="{\"role\":\"anon\",\"iss\":\"supabase\",\"iat\":$iat,\"exp\":$exp}"
service_role_payload="{\"role\":\"service_role\",\"iss\":\"supabase\",\"iat\":$iat,\"exp\":$exp}"

anon_key=$(gen_token "$anon_payload")
service_role_key=$(gen_token "$service_role_payload")

pg_meta_crypto_key=$(gen_base64 24)
s3_protocol_access_key_id=$(gen_hex 16)
s3_protocol_access_key_secret=$(gen_hex 32)
postgres_password=$(gen_hex 16)
dashboard_password=$(gen_hex 16)

echo ""
echo "JWT_SECRET=${jwt_secret}"
echo "ANON_KEY=${anon_key}"
echo "SERVICE_ROLE_KEY=${service_role_key}"
echo "PG_META_CRYPTO_KEY=${pg_meta_crypto_key}"
echo "S3_PROTOCOL_ACCESS_KEY_ID=${s3_protocol_access_key_id}"
echo "S3_PROTOCOL_ACCESS_KEY_SECRET=${s3_protocol_access_key_secret}"
echo "POSTGRES_PASSWORD=${postgres_password}"
echo "DASHBOARD_PASSWORD=${dashboard_password}"
echo ""

if [ "$1" = "--update-env" ]; then
    update_env=true
elif test -t 0; then
    printf "Update .env file? (y/N) "
    read -r REPLY
    case "$REPLY" in
        [Yy]) update_env=true ;;
        *) update_env=false ;;
    esac
else
    echo "Running non-interactively. Pass --update-env to write to .env."
    update_env=false
fi

if [ "$update_env" != "true" ]; then
    exit 0
fi

if [ ! -f .env ]; then
    echo "Error: .env not found. Copy .env.example first."
    exit 1
fi

echo "Updating .env..."

sed \
    -i.old \
    -e "s|^JWT_SECRET=.*$|JWT_SECRET=${jwt_secret}|" \
    -e "s|^ANON_KEY=.*$|ANON_KEY=${anon_key}|" \
    -e "s|^SERVICE_ROLE_KEY=.*$|SERVICE_ROLE_KEY=${service_role_key}|" \
    -e "s|^PG_META_CRYPTO_KEY=.*$|PG_META_CRYPTO_KEY=${pg_meta_crypto_key}|" \
    -e "s|^S3_PROTOCOL_ACCESS_KEY_ID=.*$|S3_PROTOCOL_ACCESS_KEY_ID=${s3_protocol_access_key_id}|" \
    -e "s|^S3_PROTOCOL_ACCESS_KEY_SECRET=.*$|S3_PROTOCOL_ACCESS_KEY_SECRET=${s3_protocol_access_key_secret}|" \
    -e "s|^POSTGRES_PASSWORD=.*$|POSTGRES_PASSWORD=${postgres_password}|" \
    -e "s|^DASHBOARD_PASSWORD=.*$|DASHBOARD_PASSWORD=${dashboard_password}|" \
    .env

echo "Done. Previous values saved to .env.old"
