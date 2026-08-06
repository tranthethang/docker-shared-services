# Secrets and Keys

How to create and rotate credentials for the minimal stack. Run scripts from `supabase/` unless noted.

## Overview

| Kind | Variables | Script |
|------|-----------|--------|
| Postgres password | `POSTGRES_PASSWORD` | [`utils/db-passwd.sh`](../utils/db-passwd.sh) (live rotate) or edit `.env` before first start |
| Legacy HS256 JWT | `JWT_SECRET`, `ANON_KEY`, `SERVICE_ROLE_KEY` | [`utils/generate-keys.sh`](../utils/generate-keys.sh) |
| Asymmetric + opaque API keys | `JWT_KEYS`, `JWT_JWKS`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`, asymmetric JWTs | [`utils/add-new-auth-keys.sh`](../utils/add-new-auth-keys.sh) |
| Opaque API key rotation only | `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY` | [`utils/rotate-new-api-keys.sh`](../utils/rotate-new-api-keys.sh) |
| Studio login | `DASHBOARD_USERNAME`, `DASHBOARD_PASSWORD` | Edit `.env`, then recreate Kong |
| Meta crypto | `PG_META_CRYPTO_KEY` | Edit `.env` before first Studio use |
| Storage S3 protocol | `S3_PROTOCOL_ACCESS_KEY_*` | Edit `.env` |

Print a subset of secrets:

```sh
cd supabase
sh run.sh secrets
```

## Generate legacy JWT keys

Requires `openssl`. Run with a `.env` present (or create one first):

```sh
cd supabase
cp .env.example .env
sh utils/generate-keys.sh              # print + prompt to update .env
sh utils/generate-keys.sh --update-env # write without interactive prompt for the update step
```

From repo root:

```sh
(cd supabase && sh utils/generate-keys.sh --update-env)
```

This sets a new `JWT_SECRET` and re-signs `ANON_KEY` / `SERVICE_ROLE_KEY`.

**Important:** Changing `JWT_SECRET` after users exist invalidates existing sessions. Prefer rotating only on fresh installs, or plan a coordinated cutover.

## Add asymmetric / opaque keys

Prerequisites: `.env` with `JWT_SECRET` already set; Node ≥ 16 **or** Docker (pulls `node:22-alpine` on first run).

```sh
cd supabase
sh utils/add-new-auth-keys.sh
sh utils/add-new-auth-keys.sh --update-env
```

Writes publishable/secret opaque keys and ES256-related fields used by Kong consumers when configured.

After updating `.env`, recreate affected services:

```sh
sh run.sh recreate supabase-kong supabase-auth supabase-storage supabase-studio
```

If you enable `GOTRUE_JWT_KEYS` / `JWT_JWKS` in Compose (commented by default), Auth and Storage must be recreated as well so they pick up JWKS verification.

## Rotate opaque API keys only

Leaves the EC key pair / JWKS untouched; regenerates `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY`.

```sh
cd supabase
sh utils/rotate-new-api-keys.sh
sh utils/rotate-new-api-keys.sh --update-env
sh run.sh recreate supabase-kong
```

Update every client that embeds the publishable key.

## Rotate Postgres password (live)

With `supabase-db` healthy:

```sh
cd supabase
sh utils/db-passwd.sh
```

The script generates a new password, updates roles inside Postgres, and writes `POSTGRES_PASSWORD` into `.env`. Then recreate services that embed the DB URL:

```sh
sh run.sh recreate supabase-auth supabase-storage supabase-meta supabase-studio
```

## Dashboard password

1. Edit `DASHBOARD_PASSWORD` (and optionally `DASHBOARD_USERNAME`) in `.env`.
2. Recreate Kong so `kong.yml` template substitution picks up the new values:

```sh
sh run.sh recreate supabase-kong
```

## Security checklist

- Never commit `.env` or printed key dumps.
- Treat `SERVICE_ROLE_KEY` / `SUPABASE_SECRET_KEY` as root — never ship them to browsers.
- Replace every default in `.env.example` before exposing ports beyond localhost.
- Prefer `ENABLE_EMAIL_AUTOCONFIRM=false` and a real SMTP relay in production.
- Restrict host firewall / bind addresses if Postgres (`SUPABASE_DB_PORT`, default `5434`) and Kong (`SUPABASE_KONG_HTTP_PORT`, default `8002`) are reachable from untrusted networks.
