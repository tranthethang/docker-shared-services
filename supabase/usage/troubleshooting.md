# Troubleshooting

Common failure modes and how to diagnose them.

## Containers exit or never become healthy

```sh
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
5. Docker has enough disk — Postgres and images are large.

## Auth or Storage cannot connect to the database

- Confirm `supabase-db` is healthy: `sh run.sh status`.
- `POSTGRES_PASSWORD` in `.env` must match the passwords applied in the running database (they diverge if you edited `.env` without rotating DB roles).
- Fix with [`utils/db-passwd.sh`](../utils/db-passwd.sh) or a full [`reset.sh`](../reset.sh) on disposable environments.

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

`run.sh` and Compose expect `docker-compose.yml` in the current working directory.

## Email confirmation never arrives

Defaults point SMTP at shared **Mailpit** (`SMTP_HOST=mailpit`, `SMTP_PORT=1025`) with `ENABLE_EMAIL_AUTOCONFIRM=false`.

1. Start Mailpit: `make up service=mailpit`
2. Open https://mailpit.localhost (or host port `8025`) to read messages
3. Or set `ENABLE_EMAIL_AUTOCONFIRM=true` to skip email locally
4. After changing SMTP env, recreate `supabase-auth`: `sh run.sh recreate supabase-auth`

## Postgres data corruption / need a clean slate

Only on disposable installs:

```sh
sh reset.sh
sh utils/generate-keys.sh --update-env
sh run.sh start
```

## Nested Compose variable interpolation

Comments in `docker-compose.yml` note that nested defaults like `${A:-${B}}` need recent Compose / podman-compose (≥ 1.6.0 for Podman). Prefer Docker Compose v2.

## Useful inspect commands

```sh
sh run.sh printenv supabase-auth
sh run.sh inspect supabase-kong
sh run.sh compose-config | less
docker compose exec supabase-db pg_isready -U postgres
```

## Still stuck?

1. Capture `sh run.sh status` and the last ~100 lines of the failing service’s logs.
2. Confirm image digests/tags in `docker-compose.yml` match what you expect after `sh run.sh pull`.
3. Diff your `.env` against `.env.example` for missing required keys.
