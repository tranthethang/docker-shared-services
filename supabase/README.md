# Supabase (minimal + Realtime)

Self-hosted Supabase pruned to **Auth + dedicated Postgres + Storage + Realtime + Studio**, behind Kong. Part of [docker-shared-services](../): shared networks (`infra_shared`, `dev_tools`), Traefik TLS, and optional Mailpit for auth email.

This stack uses its **own** Postgres (`supabase-db` on host port `5434`). It does **not** use the shared PgVector or Postgres 16 services.

## Quick start

```sh
# From repo root (preferred)
cp supabase/.env.example supabase/.env
(cd supabase && sh utils/generate-keys.sh --update-env)
make setup                    # networks + .env files if needed
make up service=traefik       # TLS for supabase.localhost
make up service=mailpit       # optional: catch auth emails
make up service=supabase

# Or from this directory
cp .env.example .env
sh utils/generate-keys.sh --update-env
sh run.sh start
```

| Resource                 | URL                                    |
| ------------------------ | -------------------------------------- |
| Studio / API (Traefik)   | https://supabase.localhost             |
| Studio / API (host port) | http://localhost:8002                  |
| Auth                     | https://supabase.localhost/auth/v1     |
| Storage                  | https://supabase.localhost/storage/v1  |
| Realtime                 | https://supabase.localhost/realtime/v1 |
| Postgres                 | `localhost:5434`                       |

Studio uses HTTP basic auth from `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` in `.env` (defaults: `admin` / `password102`).

## Services

| Compose service    | Purpose                                                         |
| ------------------ | --------------------------------------------------------------- |
| `supabase-db`      | Dedicated PostgreSQL 17 (auth / storage metadata / app schemas) |
| `supabase-auth`    | GoTrue (JWT / email / SSO hooks)                                |
| `supabase-storage` | File / object storage API (local file backend)                  |
| `realtime`         | WebSocket change feeds / broadcast / presence                   |
| `supabase-meta`    | postgres-meta for Studio                                        |
| `supabase-studio`  | Dashboard                                                       |
| `supabase-kong`    | API gateway + Traefik entrypoint                                |

**Not included:** PostgREST, GraphQL, imgproxy, Edge Functions, Logflare/Vector, Supavisor, TLS proxy overlays (Traefik handles TLS).

SMTP defaults to shared Mailpit (`mailpit:1025` on `infra_shared` / `dev_tools`).

## Port map (host)

| Variable                   | Default | Avoids clash with                  |
| -------------------------- | ------- | ---------------------------------- |
| `SUPABASE_KONG_HTTP_PORT`  | `8002`  | ChromaDB `8000`                    |
| `SUPABASE_KONG_HTTPS_PORT` | `8445`  | Appsmith `8444`                    |
| `SUPABASE_DB_PORT`         | `5434`  | PgVector `5432`, Postgres16 `5433` |

## Makefile integration

From the repo root:

```sh
make up service=supabase
make down service=supabase
make logs service=supabase
make ps
make info    # lists supabase.localhost / :8002 / DB :5434
```

Day-to-day helpers live under `supabase/` (`run.sh`, `reset.sh`, `utils/`).

## Documentation

Guides in [`usage/`](./usage/):

| Guide                                             | Description                              |
| ------------------------------------------------- | ---------------------------------------- |
| [Getting started](./usage/getting-started.md)     | Prerequisites, first boot, client wiring |
| [Architecture](./usage/architecture.md)           | Service map, removed components, volumes |
| [Configuration](./usage/configuration.md)         | `.env` reference                         |
| [Operations](./usage/operations.md)               | `run.sh`, `reset.sh`, updates, backups   |
| [Secrets and keys](./usage/secrets-and-keys.md)   | Generate / rotate JWT and API keys       |
| [API endpoints](./usage/api-endpoints.md)         | Kong routes and what is not exposed      |
| [Troubleshooting](./usage/troubleshooting.md)     | Common failures and diagnostics          |
| [Repository layout](./usage/repository-layout.md) | File and folder map                      |

## Helpers

Run from `supabase/` (or prefix with `(cd supabase && …)`):

```sh
sh run.sh start|stop|status|logs   # day-to-day Compose wrapper
sh reset.sh                        # wipe containers + bind-mounted data
sh utils/generate-keys.sh          # JWT + legacy anon/service keys
sh utils/add-new-auth-keys.sh      # asymmetric + opaque API keys
sh utils/rotate-new-api-keys.sh    # rotate opaque keys only
sh utils/db-passwd.sh              # rotate Postgres password live
sh utils/reassign-owner.sh         # reassign schema ownership to postgres
```

## License / upstream

Derived from the [Supabase](https://github.com/supabase/supabase) Docker self-hosting layout, reduced for a minimal footprint inside this shared-services repo.
