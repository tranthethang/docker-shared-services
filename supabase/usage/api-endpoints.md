# API Endpoints

Kong listens on container ports `8000` / `8443`, published as `SUPABASE_KONG_HTTP_PORT` / `SUPABASE_KONG_HTTPS_PORT` (defaults **8002** / **8445**). Traefik routes:

- APIs → `https://supabase.localhost`
- Studio → `https://studio.dss.localhost`

Preferred API base URL: `https://supabase.localhost` (`SUPABASE_PUBLIC_URL`). Direct host access: `http://localhost:8002`.

Declarative routes live in [`volumes/api/kong.yml`](../volumes/api/kong.yml).

## Public Auth routes (no API key)

| Path                                      | Upstream                     |
| ----------------------------------------- | ---------------------------- |
| `/auth/v1/verify`                         | Auth verify                  |
| `/auth/v1/callback`                       | OAuth callback               |
| `/auth/v1/authorize`                      | OAuth authorize              |
| `/auth/v1/.well-known/jwks.json`          | JWKS                         |
| `/auth/v1/sso/saml/acs`                   | SAML ACS                     |
| `/auth/v1/sso/saml/metadata`              | SAML metadata                |
| `/.well-known/oauth-authorization-server` | OAuth AS metadata (RFC 8414) |

## Auth API (API key)

| Path         | Notes                                                                     |
| ------------ | ------------------------------------------------------------------------- |
| `/auth/v1/*` | GoTrue — send `apikey` header with anon/publishable or service/secret key |

Example:

```sh
curl 'https://supabase.localhost/auth/v1/health' \
  -H "apikey: $ANON_KEY"
```

## Realtime

| Path                       | Notes                                                              |
| -------------------------- | ------------------------------------------------------------------ |
| `/realtime/v1/`            | WebSocket (`protocol: ws`) — phoenix socket for channels / changes |
| `/realtime/v1/api/*`       | HTTP Realtime API (key-auth + ACL)                                 |
| `/realtime/v1/api/openapi` | Blocked (`403`)                                                    |
| `/realtime/v1/api/tenants` | Blocked (`403`)                                                    |

Clients connect via the Supabase JS client (`supabase.channel(...)`). The SDK uses `SUPABASE_PUBLIC_URL` and the anon/publishable key; Kong forwards WebSocket traffic to `realtime-dev.supabase-realtime:4000`.

Health (from inside the Realtime container / compose network):

```sh
curl -sSfL -H "Authorization: Bearer $ANON_KEY" \
  http://realtime-dev.supabase-realtime:4000/api/tenants/realtime-dev/health
```

## Storage API

| Path            | Notes                                                       |
| --------------- | ----------------------------------------------------------- |
| `/storage/v1/*` | File/object API; max upload size 50 MiB (`FILE_SIZE_LIMIT`) |

No Kong `key-auth` on Storage (S3 protocol / SigV4 and user JWTs). Image transforms are **disabled** (no imgproxy).

## Meta (admin API key)

| Path    | Notes                                                            |
| ------- | ---------------------------------------------------------------- |
| `/pg/*` | postgres-meta — requires service_role / secret key (`admin` ACL) |

## Studio / dashboard

| Path                     | Auth                                                       |
| ------------------------ | ---------------------------------------------------------- |
| `/` and Studio UI routes | Direct un-gated local dev access on `studio.dss.localhost` |

Open https://studio.dss.localhost for direct access. Non-API paths on https://supabase.localhost redirect there.

## MCP

| Path       | Behavior                                                                      |
| ---------- | ----------------------------------------------------------------------------- |
| `/api/mcp` | Blocked (`403`)                                                               |
| `/mcp`     | Blocked by default (`403`); can be opened for local IPs by editing `kong.yml` |

## Postgres

Direct TCP access (no pooler):

```
host: localhost
port: 5434          # SUPABASE_DB_PORT (container listens on 5432)
database: postgres  # POSTGRES_DB
user: postgres
password: <POSTGRES_PASSWORD>
```

There is **no** `/rest/v1` PostgREST endpoint in this stack. Query Postgres with SQL, your own backend, or Studio.

## Not available

These paths exist in full Supabase deployments but are **not** routed here:

- `/rest/v1` — PostgREST
- `/functions/v1` — Edge Functions
- `/graphql/v1` — GraphQL
- Analytics / Logs Explorer APIs

## Kong configuration

Entrypoint substitutes env placeholders: [`volumes/api/kong-entrypoint.sh`](../volumes/api/kong-entrypoint.sh). Realtime WebSocket `apikey` query params are rewritten via `LUA_RT_WS_EXPR`.

After editing `kong.yml` or related env vars:

```sh
cd supabase
sh run.sh recreate supabase-kong
```
