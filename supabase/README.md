# Supabase (minimal + Realtime)

Self-hosted Supabase pruned to **Auth + dedicated Postgres + Storage + Realtime + Studio**, behind Kong. Part of [docker-shared-services](../): shared networks (`infra_shared`, `dev_tools`), Traefik TLS, and optional Mailpit for auth email.

This stack uses its **own** Postgres (`supabase-db` on host port `5434`). It does **not** use the shared PgVector or Postgres 16 services.

## Quick start

```sh
# From repo root (preferred)
cp supabase/.env.example supabase/.env
(cd supabase && sh utils/generate-keys.sh --update-env)
make setup                    # networks + .env files if needed
make up service=traefik       # TLS
make up service=mailpit       # optional: catch auth emails
make up service=supabase

# Or from this directory
cp .env.example .env
sh utils/generate-keys.sh --update-env
sh run.sh start
```

| Resource              | URL                                        |
| --------------------- | ------------------------------------------ |
| Studio (Traefik)      | https://studio.dss.localhost               |
| API gateway (Traefik) | https://supabase.dss.localhost             |
| Auth                  | https://supabase.dss.localhost/auth/v1     |
| Storage               | https://supabase.dss.localhost/storage/v1  |
| Realtime              | https://supabase.dss.localhost/realtime/v1 |
| Postgres              | `localhost:5434`                           |

Studio UI is open directly for local development at https://studio.dss.localhost. Visiting https://supabase.dss.localhost redirects Studio UI to https://studio.dss.localhost.

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

| Variable           | Default | Avoids clash with                  |
| ------------------ | ------- | ---------------------------------- |
| `SUPABASE_DB_PORT` | `5434`  | PgVector `5432`, Postgres16 `5433` |

## Database storage & migration

`supabase-db` data directory (`/var/lib/postgresql/data`) is backed by a Docker named volume (`supabase_db_data`) rather than the host bind mount (`./volumes/db/data`). This avoids severe filesystem synchronization bottlenecks and permission friction on macOS Docker Desktop.

### Migrating existing host-path data

If you previously ran Supabase with data in `./volumes/db/data`:

1. **Dump / Restore (recommended)**:
   Before switching or using the previous bind mount:

   ```sh
   pg_dump -h 127.0.0.1 -p 5434 -U postgres -d postgres -F c -b -v -f supabase_backup.dump
   ```

   Start the new stack with `supabase_db_data`:

   ```sh
   make up service=supabase
   pg_restore -h 127.0.0.1 -p 5434 -U postgres -d postgres -v supabase_backup.dump
   ```

1. **File copy into an empty named volume**:
   Use this only before starting the updated Supabase stack, while the database is stopped. The target volume must be empty; do not copy files over a volume that PostgreSQL has already initialized. From the repository root:

   ```sh
   make down service=supabase
   docker volume create supabase_db_data
   docker run --rm --mount type=bind,src="$(pwd)/supabase/volumes/db/data",dst=/src,readonly --mount type=volume,src=supabase_db_data,dst=/dst alpine cp -a /src/. /dst/
   ```

   Ensure permissions remain owned by PostgreSQL (`uid 999` or the image's postgres user), then start the stack. If `supabase_db_data` has already been initialized, use the dump/restore method above instead of overlaying files.

## Makefile integration

From the repo root:

```sh
make up service=supabase
make down service=supabase
make logs service=supabase
make ps
make info    # lists the Supabase domains and DB :5434
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
