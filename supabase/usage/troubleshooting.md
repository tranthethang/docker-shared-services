# Troubleshooting

Common failure modes and how to diagnose them. Prefer `make` from the repo root, or `sh run.sh …` from `supabase/`.

## Containers exit or never become healthy

```sh
cd supabase
sh run.sh status
sh run.sh logs
sh run.sh logs supabase-db
sh run.sh logs supabase-auth
```

Check:

1. `.env` exists and was filled from `.env.example`.
2. `JWT_SECRET` is at least 32 characters; `PG_META_CRYPTO_KEY` likewise.
3. Host ports `8002`, `8445`, and `5434` are free (or change `SUPABASE_KONG_*` / `SUPABASE_DB_PORT`).
4. Shared networks exist: `make setup` (creates `infra_shared` / `dev_tools`).
5. Required volume files exist (`volumes/api/kong.yml`, `volumes/db/*.sql`, `volumes/api/kong-entrypoint.sh`).
6. Docker has enough disk — Postgres and images are large.

## `supabase.localhost` does not resolve / TLS fails

1. Start Traefik: `make up service=traefik`
2. Confirm `SUPABASE_SUBDOMAIN` / `DOMAIN_NAME` / `SUPABASE_PUBLIC_URL` match your Traefik host rule.
3. Use host port fallback: http://localhost:8002

## Auth or Storage cannot connect to the database

- Confirm `supabase-db` is healthy: `sh run.sh status`.
- `POSTGRES_PASSWORD` in `.env` must match the passwords applied in the running database (they diverge if you edited `.env` without rotating DB roles).
- Fix with [`utils/db-passwd.sh`](../utils/db-passwd.sh) or a full [`reset.sh`](../reset.sh) on disposable environments.

## Auth crash: `must be owner of function uid`

GoTrue migrations fail if `auth.uid` / `auth.role` / `auth.email` are still owned by `postgres`. Fresh installs apply [`volumes/db/auth-owner.sql`](../volumes/db/auth-owner.sql) on first boot. On an already-initialized DB:

```sh
# From supabase/ with POSTGRES_PASSWORD loaded from .env
docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" supabase-db \
  psql -h 127.0.0.1 -U supabase_admin -d postgres \
  -c "ALTER FUNCTION auth.uid() OWNER TO supabase_auth_admin;" \
  -c "ALTER FUNCTION auth.role() OWNER TO supabase_auth_admin;" \
  -c "ALTER FUNCTION auth.email() OWNER TO supabase_auth_admin;"
docker restart supabase-auth
```

## Studio shows login but APIs return 401

- Use the current `ANON_KEY` / `SERVICE_ROLE_KEY` (or opaque keys) from `.env`.
- After regenerating keys, recreate `supabase-kong` (and usually `supabase-auth` / `supabase-storage` / `supabase-studio`).
- Dashboard basic-auth failures mean `DASHBOARD_*` mismatch — recreate `supabase-kong` after edits.

## “No such file” / scripts fail

Run helpers from the **supabase directory** (or use `make up service=supabase` from repo root):

```sh
cd /path/to/docker-shared-services/supabase
sh run.sh start
sh utils/generate-keys.sh --update-env
```

`run.sh` and Compose expect `docker-compose.yml` next to the script. Use full Compose service names (`supabase-db`, not `db`).

## Email confirmation never arrives

Defaults point SMTP at shared **Mailpit** (`SMTP_HOST=mailpit`, `SMTP_PORT=1025`) with `ENABLE_EMAIL_AUTOCONFIRM=false`.

1. Start Mailpit: `make up service=mailpit`
2. Open https://mailpit.localhost (or host port `8025`) to read messages
3. Or set `ENABLE_EMAIL_AUTOCONFIRM=true` to skip email locally
4. After changing SMTP env, recreate auth: `sh run.sh recreate supabase-auth`

## Postgres data corruption / need a clean slate

Only on disposable installs:

```sh
cd supabase
sh reset.sh
sh utils/generate-keys.sh --update-env
sh run.sh start
```

## Nested Compose variable interpolation

Prefer Docker Compose v2. Nested defaults like `${A:-${B}}` need recent Compose / podman-compose (≥ 1.6.0 for Podman).

## Useful inspect commands

```sh
cd supabase
sh run.sh printenv supabase-auth
sh run.sh inspect supabase-kong
sh run.sh compose-config | less
docker compose exec supabase-db pg_isready -U postgres
```

## Still stuck?

1. Capture `sh run.sh status` and the last ~100 lines of the failing service’s logs.
2. Confirm image digests/tags in `docker-compose.yml` match what you expect after `sh run.sh pull`.
3. Diff your `.env` against `.env.example` for missing required keys.
