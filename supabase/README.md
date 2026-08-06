# Supabase (minimal)

Self-hosted Supabase pruned to **Identity (Auth) + Catalog DB + Asset Storage + Studio**, integrated with this repo’s shared networks and Traefik.

## Quick start

```sh
# From repo root (preferred)
cp supabase/.env.example supabase/.env
(cd supabase && sh utils/generate-keys.sh --update-env)
make setup                    # networks + .env files if needed
make up service=mailpit       # optional: catch auth emails
make up service=supabase

# Or from this directory
cp .env.example .env
sh utils/generate-keys.sh --update-env
sh run.sh start
```

| Resource | URL |
|----------|-----|
| Studio / API (Traefik) | https://supabase.localhost |
| Studio / API (host port) | http://localhost:8002 |
| Auth | https://supabase.localhost/auth/v1 |
| Storage | https://supabase.localhost/storage/v1 |
| Postgres | `localhost:5434` |

Studio uses HTTP basic auth from `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` in `.env` (defaults: `admin` / `password102`).

## Services

| Compose service | Purpose |
|-----------------|---------|
| `supabase-db` | PostgreSQL catalog / auth / storage metadata |
| `supabase-auth` | GoTrue (JWT / SSO hooks) |
| `supabase-storage` | File / object storage API |
| `supabase-meta` | postgres-meta for Studio |
| `supabase-studio` | Dashboard |
| `supabase-kong` | API gateway (Traefik entrypoint) |

**Removed:** PostgREST, Realtime, GraphQL, imgproxy, Edge Functions, Logflare/Vector, Supavisor, TLS proxy overlays.

Networks: `infra_shared` + `dev_tools` (same as other stacks). SMTP defaults to Mailpit (`mailpit:1025`).

## Port map (host)

| Variable | Default | Avoids clash with |
|----------|---------|-------------------|
| `SUPABASE_KONG_HTTP_PORT` | `8002` | ChromaDB `8000` |
| `SUPABASE_KONG_HTTPS_PORT` | `8445` | Appsmith `8444` |
| `SUPABASE_DB_PORT` | `5434` | PgVector `5432`, Postgres16 `5433` |

## Documentation

Detailed guides in [`usage/`](./usage/):

| Guide | Description |
|-------|-------------|
| [Getting started](./usage/getting-started.md) | Prerequisites, first boot, client wiring |
| [Architecture](./usage/architecture.md) | Service map, removed components, volumes |
| [Configuration](./usage/configuration.md) | `.env` reference |
| [Operations](./usage/operations.md) | `run.sh`, `reset.sh`, updates, backups |
| [Secrets and keys](./usage/secrets-and-keys.md) | Generate / rotate JWT and API keys |
| [API endpoints](./usage/api-endpoints.md) | Kong routes and what is not exposed |
| [Troubleshooting](./usage/troubleshooting.md) | Common failures and diagnostics |
| [Repository layout](./usage/repository-layout.md) | File and folder map |

## Helpers

```sh
sh run.sh start|stop|status|logs   # day-to-day Compose wrapper
sh reset.sh                        # wipe containers + bind-mounted data
sh utils/generate-keys.sh          # JWT + legacy anon/service keys
sh utils/add-new-auth-keys.sh      # asymmetric + opaque API keys
sh utils/rotate-new-api-keys.sh    # rotate opaque keys only
sh utils/db-passwd.sh              # rotate Postgres password live
```

## License / upstream

Derived from the [Supabase](https://github.com/supabase/supabase) Docker self-hosting layout, reduced for a minimal production-adjacent footprint.
