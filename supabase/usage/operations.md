# Operations

Day-to-day management via the repo **Makefile** (preferred) or local helpers [`run.sh`](../run.sh) / [`reset.sh`](../reset.sh).

## Makefile (repo root)

```sh
make up service=supabase
make down service=supabase
make stop service=supabase
make restart service=supabase
make logs service=supabase
make ps
```

Ensure networks exist first (`make setup`) and start Traefik if you use `https://supabase.localhost`.

## `run.sh` (from `supabase/`)

`run.sh` changes into its own directory before calling Compose. Service names must match Compose (e.g. `supabase-auth`, not `auth`).

```sh
cd supabase

sh run.sh start                 # docker compose up -d --wait
sh run.sh stop                  # docker compose down
sh run.sh restart [service]     # restart all or named services
sh run.sh recreate [service]    # force-recreate (full stack or one service)
sh run.sh status                # docker compose ps
sh run.sh logs [service]        # follow logs
sh run.sh pull                  # pull images
sh run.sh secrets               # print selected secrets from .env
sh run.sh help
```

### Restart / recreate filters

```sh
# Restart everything except the database
sh run.sh restart --except supabase-db

# Force-recreate auth only (leave dependencies running)
sh run.sh recreate supabase-auth

# Force-recreate all except db
sh run.sh recreate --except supabase-db
```

### Inspection

```sh
sh run.sh inspect supabase-auth          # docker inspect on the auth container
sh run.sh printenv supabase-storage      # print container env vars
sh run.sh compose-config                 # fully resolved Compose config
```

### Compose file list (`COMPOSE_FILE`)

`.env` may list colon-separated Compose files. Manage them without hand-editing:

```sh
sh run.sh config                # show active list
sh run.sh config add override   # adds docker-compose.override.yml if the file exists
sh run.sh config remove override
```

This service ships only `docker-compose.yml`; override files are optional (`docker-compose.override.yml` is gitignored).

## Direct Docker Compose

From `supabase/`:

```sh
docker compose up -d --wait
docker compose down
docker compose ps
docker compose logs -f supabase-auth
docker compose pull
```

From repo root (same pattern as `make`):

```sh
docker compose -f docker-compose.shared.yml -f supabase/docker-compose.yml up -d
```

## Full reset

[`reset.sh`](../reset.sh) **destroys** containers, named volumes, bind-mounted data, and optionally restores `.env` from `.env.example`. Run from `supabase/`:

```sh
cd supabase
sh reset.sh          # interactive confirmations
sh reset.sh -y       # skip prompts (still destructive)
```

What it does:

1. `docker compose down -v --remove-orphans`
2. Removes `./volumes/db/data` and `./volumes/storage` (with confirm)
3. Renames `.env` → `.env.old` and copies `.env.example` → `.env`

After reset:

```sh
sh utils/generate-keys.sh --update-env
sh run.sh pull
sh run.sh start
```

## Updating images

```sh
cd supabase
sh run.sh pull
sh run.sh recreate
```

Pin versions by editing image tags in `docker-compose.yml`.

## Backups (recommended practice)

This repo does not include a backup tool. At minimum:

1. Stop or quiesce writes if you need a consistent dump.
2. Dump Postgres:

   ```sh
   cd supabase
   docker compose exec supabase-db pg_dumpall -U postgres > backup.sql
   ```

3. Archive `./volumes/storage` for file objects.
4. Keep a secure copy of `.env` (secrets) offline.

## Reassign schema ownership

If Studio or migrations need objects owned by `postgres` instead of `supabase_admin`:

```sh
cd supabase
sh utils/reassign-owner.sh
```

See the [upstream guide](https://supabase.com/docs/guides/self-hosting/remove-superuser-access).
