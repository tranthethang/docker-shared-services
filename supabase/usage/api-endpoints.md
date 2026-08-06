# API Endpoints

Kong listens on container ports `8000` / `8443`, published as `SUPABASE_KONG_HTTP_PORT` / `SUPABASE_KONG_HTTPS_PORT` (defaults **8002** / **8445**). Traefik also routes `https://supabase.localhost` to Kong.

Preferred base URL: `https://supabase.localhost` (`SUPABASE_PUBLIC_URL`). Direct host access: `http://localhost:8002`.

## Public Auth routes (no API key)

| Path | Upstream |
|------|----------|
| `/auth/v1/verify` | Auth verify |
| `/auth/v1/callback` | OAuth callback |
| `/auth/v1/authorize` | OAuth authorize |
| `/auth/v1/.well-known/jwks.json` | JWKS |

## Auth API (API key)

| Path | Notes |
|------|-------|
| `/auth/v1/*` | GoTrue — send `apikey` header with anon/publishable or service/secret key |

Example:

```sh
curl 'https://supabase.localhost/auth/v1/health' \
  -H "apikey: $ANON_KEY"
```

## Storage API

| Path | Notes |
|------|-------|
| `/storage/v1/*` | File/object API; max upload size 50 MiB (`FILE_SIZE_LIMIT`) |

Image transforms are **disabled** (no imgproxy).

## Studio / dashboard

| Path | Auth |
|------|------|
| `/` and Studio UI routes | HTTP basic auth (`DASHBOARD_*`) |
| Internal Meta via Studio | Not exposed as a first-class public REST surface in the same way as Auth/Storage |

Open http://localhost:8000 and sign in with the dashboard credentials from `.env`.

## Postgres

Direct TCP access (no pooler):

```
host: localhost
port: 5432          # POSTGRES_PORT
database: postgres  # POSTGRES_DB
user: postgres
password: <POSTGRES_PASSWORD>
```

There is **no** `/rest/v1` PostgREST endpoint in this stack. Query Postgres with SQL, your own backend, or Studio.

## Not available

These paths exist in full Supabase deployments but are **not** routed here:

- `/rest/v1` — PostgREST
- `/realtime/v1` — Realtime
- `/functions/v1` — Edge Functions
- `/graphql/v1` — GraphQL
- Analytics / Logs Explorer APIs

## Kong configuration

Declarative config: [`volumes/api/kong.yml`](../volumes/api/kong.yml).  
Entrypoint substitutes env placeholders: [`volumes/api/kong-entrypoint.sh`](../volumes/api/kong-entrypoint.sh).

After editing `kong.yml` or related env vars:

```sh
sh run.sh recreate supabase-kong
```
