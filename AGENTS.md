# AGENTS.md

## Project

Local Docker Compose infrastructure for development (databases, cache, auth, CI, observability). Each service is its own Compose project, started from the root Makefile via `bin/service_manager.py`. Web UIs are reached through Traefik at `https://*.dss.localhost`.

## Commands

```bash
make setup                              # networks + .env (interactive; needs a TTY)
make up service=zitadel                 # one service; queues its backends first
make down service=zitadel               # stop and remove that service's containers
make ps                                 # status of running services
make health service=postgres            # health for one service
make logs service=zitadel               # logs for one service
make check                              # format, lint, typecheck, test, and Compose validate
make test-update                        # regenerate tests/golden (GOLDEN_UPDATE=1)
```

Validate one Compose file:

```bash
docker compose --project-directory zitadel \
  -f docker-compose.shared.yml -f zitadel/docker-compose.yml config -q
```

`make tui` and `make package` need `uv` plus a TTY. The commands above do not.

## Structure

- `bin/` — orchestration (`service_manager.py`, `env_manager.py`, `config.py`)
- `<service>/` — that service's `docker-compose.yml` and `.env.example`
- `docker-compose.shared.yml` — external networks `traefik_proxy`, `backend_net`, `data_net`
- `traefik/` — reverse proxy
- `docs/` — usage, configuration, networking, troubleshooting
- `dist/` — export from `make package`; gitignored

## Conventions

- Write files in this repo in English (README, `docs/`, comments, commits, `.env.example`).
- Load a service with `--project-directory <service>` so `<service>/.env` and relative paths resolve.
- Publish web UIs with Traefik labels. Bind database and protocol ports to `127.0.0.1` only.
- Record cross-project backends in `PACKAGE_REQUIRES` in `bin/config.py` (`postgres` → `zitadel`, `zitadel` → `oauth2-proxy`).
- Use `uv` for `make sync`, `make format`, `make check`, `make tui`, and `make package`. `make up` and `make down` still call `python3 bin/...`.

## Gotchas

- `depends_on` does not cross Compose projects. `make up service=<name>` must start that service's `dependency_queue` and wait until each backend container is `running` and, when a healthcheck exists, `healthy`. A created container is not ready.
- `make up` without `service=` opens a menu. Pass `service=<name>`.
- `make setup` prompts before writing `.env` files and certificates. Skip it when there is no TTY.
- Root `.env` must exist before `make up`. Create it with `make setup`.
- Setup rejects the legacy password `Password102!`.

## Workflow

- After Compose, shell, or `bin/` edits, run `make check`. It runs `format-check`, `lint`, `typecheck`, `test`, and `validate`. Regenerate exporter snapshots with `make test-update` when `export_stack` output changes on purpose.
- Ask before adding dependencies, committing, or pushing.
- Create a commit only when the user asks.

## Limits

- **NEVER** edit or test under `dist/`. Change the origin tree (`Makefile`, `bin/`, service directories). Leave `dist/` empty unless the user asks for a new export.
- Do not commit `.env` files or `traefik/certs/*.{crt,key}`.
- Do not run `make remove-all`, `make prune`, or `make remove-config` unless the user asks. They delete data or env files.

## More docs

- Commands: `docs/usage.md`
- Configuration: `docs/configuration.md`
- Networks: `docs/network-segmentation.md`
- Service URLs: `make info` and `docs/services.md`
- Troubleshooting: `docs/troubleshooting.md`
