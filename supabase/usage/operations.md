# Operations

Day-to-day management of the stack using [`run.sh`](../run.sh) and [`reset.sh`](../reset.sh).

All commands assume you are in the **repository root** (where `docker-compose.yml` lives).

## `run.sh` cheat sheet

```sh
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
sh run.sh restart --except db

# Force-recreate auth only (leave dependencies running)
sh run.sh recreate auth

# Force-recreate all except db
sh run.sh recreate --except db
```

### Inspection

```sh
sh run.sh inspect auth          # docker inspect on the auth container
sh run.sh printenv storage      # print container env vars
sh run.sh compose-config        # fully resolved Compose config
```

### Compose file list (`COMPOSE_FILE`)

`.env` may list colon-separated Compose files. Manage them without hand-editing:

```sh
sh run.sh config                # show active list
sh run.sh config add pg17       # adds docker-compose.pg17.yml if the file exists
sh run.sh config remove pg17
```

This minimal repo ships only `docker-compose.yml`; override files are optional for your own customizations (e.g. `docker-compose.override.yml` is gitignored).

## Direct Docker Compose

```sh
docker compose up -d
docker compose down
docker compose ps
docker compose logs -f auth
docker compose pull
```

## Full reset

[`reset.sh`](../reset.sh) **destroys** containers, named volumes, bind-mounted data, and optionally restores `.env` from `.env.example`.

```sh
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
docker compose pull
sh run.sh start
```

## Updating images

```sh
sh run.sh pull
sh run.sh recreate
```

Pin versions by editing image tags in `docker-compose.yml`.

## Backups (recommended practice)

This repo does not include a backup tool. At minimum:

1. Stop or quiesce writes if you need a consistent dump.
2. Dump Postgres: `docker compose exec db pg_dumpall -U postgres > backup.sql`
3. Archive `./volumes/storage` for file objects.
4. Keep a secure copy of `.env` (secrets) offline.

## Reassign schema ownership

If Studio or migrations need objects owned by `postgres` instead of `supabase_admin`:

```sh
sh utils/reassign-owner.sh
```

See the [upstream guide](https://supabase.com/docs/guides/self-hosting/remove-superuser-access).
