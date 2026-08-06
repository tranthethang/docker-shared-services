# Configuration

All runtime settings live in `supabase/.env` (copied from [`.env.example`](../.env.example)). Never commit `.env`.

Prefer starting via the repo Makefile (`make up service=supabase`) so shared networks exist. Local helpers (`run.sh`) read `COMPOSE_FILE` from `.env` when you work inside `supabase/`.

## Secrets (change before first start)

| Variable                                                      | Description                                                    |
| ------------------------------------------------------------- | -------------------------------------------------------------- |
| `POSTGRES_PASSWORD`                                           | Shared password for Postgres roles used by Auth/Storage        |
| `JWT_SECRET`                                                  | Legacy HS256 signing secret (min 32 characters)                |
| `ANON_KEY`                                                    | Legacy anon JWT (signed with `JWT_SECRET`)                     |
| `SERVICE_ROLE_KEY`                                            | Legacy service_role JWT — **server-side only**                 |
| `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`                   | Kong basic-auth for Studio (defaults: `admin` / `password102`) |
| `PG_META_CRYPTO_KEY`                                          | Studio ↔ postgres-meta encryption (min 32 chars)               |
| `SECRET_KEY_BASE`                                             | Realtime Phoenix secret (min 64 chars)                         |
| `REALTIME_DB_ENC_KEY`                                         | Realtime `_realtime` field encryption (exactly 16 chars)       |
| `S3_PROTOCOL_ACCESS_KEY_ID` / `S3_PROTOCOL_ACCESS_KEY_SECRET` | Storage S3-protocol credentials                                |

Generate JWT + legacy API keys with:

```sh
cd supabase
sh utils/generate-keys.sh --update-env
```

Optional asymmetric / opaque keys:

| Variable                                              | Description                                   |
| ----------------------------------------------------- | --------------------------------------------- |
| `SUPABASE_PUBLISHABLE_KEY`                            | Opaque public API key                         |
| `SUPABASE_SECRET_KEY`                                 | Opaque secret API key                         |
| `JWT_KEYS` / `JWT_JWKS`                               | EC signing material (when enabled in Compose) |
| `ANON_KEY_ASYMMETRIC` / `SERVICE_ROLE_KEY_ASYMMETRIC` | ES256 JWT variants for Kong                   |

See [Secrets and keys](./secrets-and-keys.md).

## URLs (Traefik)

| Variable                             | Typical local value                  | Notes                                  |
| ------------------------------------ | ------------------------------------ | -------------------------------------- |
| `SUPABASE_PUBLIC_URL`                | `https://supabase.localhost`         | Public base URL for clients / Storage  |
| `API_EXTERNAL_URL`                   | `https://supabase.localhost/auth/v1` | External Auth base (issuer, redirects) |
| `SITE_URL`                           | `https://supabase.localhost`         | App site URL for Auth redirects        |
| `SUPABASE_SUBDOMAIN` / `DOMAIN_NAME` | `supabase` / `localhost`             | Traefik `Host()` rule                  |
| `ADDITIONAL_REDIRECT_URLS`           | *(empty)*                            | Comma-separated allow-list             |

## Database

| Variable           | Default       | Notes                                                             |
| ------------------ | ------------- | ----------------------------------------------------------------- |
| `POSTGRES_HOST`    | `supabase-db` | Compose service name                                              |
| `POSTGRES_DB`      | `postgres`    | Database name                                                     |
| `POSTGRES_PORT`    | `5432`        | **Container-internal** port (used by Auth/Storage/Realtime/Meta) |
| `SUPABASE_DB_PORT` | `5434`        | **Host** publish port (avoids pgvector `5432`, postgres16 `5433`) |

This is a dedicated Supabase Postgres image, not the shared `pgvector` / `postgres` services. To point at an **external** Postgres, comment out the `supabase-db` service and related `depends_on` health checks in `docker-compose.yml`, then set `POSTGRES_HOST` / credentials accordingly.

## Studio

| Variable                      | Description                   |
| ----------------------------- | ----------------------------- |
| `STUDIO_DEFAULT_ORGANIZATION` | Default org name in Studio    |
| `STUDIO_DEFAULT_PROJECT`      | Default project name          |
| `OPENAI_API_KEY`              | Optional — Studio AI features |

Logs Explorer is disabled (`ENABLED_FEATURES_LOGS_ALL=false`) because analytics is not deployed.

## Auth

| Variable                   | Default            | Notes                                                     |
| -------------------------- | ------------------ | --------------------------------------------------------- |
| `JWT_EXPIRY`               | `3600`             | Access token TTL (seconds)                                |
| `DISABLE_SIGNUP`           | `false`            | Block new signups when `true`                             |
| `ENABLE_EMAIL_SIGNUP`      | `true`             | Email/password signup                                     |
| `ENABLE_EMAIL_AUTOCONFIRM` | `false`            | Use Mailpit (`SMTP_HOST=mailpit`) for confirmation emails |
| `ENABLE_ANONYMOUS_USERS`   | `false`            | Anonymous sign-in                                         |
| `ENABLE_PHONE_SIGNUP`      | `false`            | Phone auth                                                |
| `SMTP_HOST` / `SMTP_PORT`  | `mailpit` / `1025` | Shared Mailpit on `infra_shared`                          |

OAuth, SAML, MFA, and Auth hooks can be added under the `supabase-auth` service when needed.

## Realtime

| Variable              | Default            | Notes                                                                 |
| --------------------- | ------------------ | --------------------------------------------------------------------- |
| `SECRET_KEY_BASE`     | *(see `.env.example`)* | Phoenix secret; regenerate for non-dev (`openssl rand -base64 48`) |
| `REALTIME_DB_ENC_KEY` | `supabaserealtime` | Exactly 16 characters (`openssl rand -hex 8`)                         |

Compose service name is `realtime`; container name is fixed as `realtime-dev.supabase-realtime`. Resource limits: `SUPABASE_REALTIME_CPUS_*` / `SUPABASE_REALTIME_MEMORY_*`.

## Storage

| Variable            | Default | Notes                           |
| ------------------- | ------- | ------------------------------- |
| `GLOBAL_S3_BUCKET`  | `stub`  | Directory name for file backend |
| `REGION`            | `stub`  | Required by Storage API         |
| `STORAGE_TENANT_ID` | `stub`  | Tenant id                       |

Default backend is **file** under `./volumes/storage`. Image transforms are off.

## Kong host ports

| Variable                   | Default | Avoids          |
| -------------------------- | ------- | --------------- |
| `SUPABASE_KONG_HTTP_PORT`  | `8002`  | ChromaDB `8000` |
| `SUPABASE_KONG_HTTPS_PORT` | `8445`  | Appsmith `8444` |

Traefik terminates TLS on `supabase.localhost`; host ports remain available for direct access.

## Resource limits

Each Compose service has `deploy.resources` limits/reservations via `SUPABASE_*_CPUS_*` and `SUPABASE_*_MEMORY_*` (see `.env.example`). `RESTART_POLICY` defaults to `always`.