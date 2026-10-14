# AGENTS.md

## Project

Local Docker Compose infrastructure for development (databases, cache, auth, CI, observability). Each service is its own Compose project, started from the root Makefile via `python -m dss.cli.service` (run through `uv`). Web UIs are reached through Traefik at `https://*.dss.localhost`.

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

Every target that runs Python needs `uv`; the Makefile stops with an install hint when it is missing. `make tui` and `make package` also need a TTY.

## Structure

- `dss/` — Python package, one layer per subpackage (enforced by `lint-imports`):
  - `dss/core/` — `config.py`, `service_catalog.py` + `.json`, `utils.py`, `env_manager.py`. Standard library only.
  - `dss/cli/` — `service.py` (`make up/down/…`), `env.py` (`make setup`, env commands), `checkbox_menu.py`
  - `dss/package/` — `export.py` (`export_stack`) and `wizard.py` (`make package`)
  - `dss/tui/` — Textual dashboard (`make tui`)
- `tools/` — dev tooling (`format_repo.py`, `check_file_size.py` + baseline)
- `scripts/` — shell scripts only
- `<service>/` — that service's `docker-compose.yml` and `.env.example`
- `docker-compose.shared.yml` — external networks `traefik_proxy`, `backend_net`, `data_net`
- `traefik/` — reverse proxy
- `docs/` — usage, configuration, networking, troubleshooting
- `dist/` — export from `make package`; gitignored

## Conventions

- Write files in this repo in English (README, `docs/`, comments, commits, `.env.example`).
- Load a service with `--project-directory <service>` so `<service>/.env` and relative paths resolve.
- Publish web UIs with Traefik labels. Bind database and protocol ports to `127.0.0.1` only.
- Record cross-project backends in `PACKAGE_REQUIRES` in `dss/core/config.py` (`postgres` → `zitadel`, `zitadel` → `oauth2-proxy`).
- Run Python as modules from the repo root through `uv` (`uv run --frozen --no-dev python -m dss.cli.env …`). Imports are absolute (`from dss.core.config import …`); do not add `sys.path` hacks.
- `dss.core` imports nothing from `dss.cli`, `dss.package`, or `dss.tui`; `dss.cli` and `dss.package` do not import each other or `dss.tui`.

## Gotchas

- `depends_on` does not cross Compose projects. `make up service=<name>` must start that service's `dependency_queue` and wait until each backend container is `running` and, when a healthcheck exists, `healthy`. A created container is not ready.
- `make up` without `service=` opens a menu. Pass `service=<name>`.
- `make setup` prompts before writing `.env` files and certificates. Skip it when there is no TTY.
- Root `.env` must exist before `make up`. Create it with `make setup`.
- Setup rejects the legacy password `Password102!`.

## Workflow

- After Compose, shell, or `dss/` edits, run `make check`. It runs `format-check`, `lint`, `typecheck`, `test`, and `validate`. Regenerate exporter snapshots with `make test-update` when `export_stack` output changes on purpose.
- Ask before adding dependencies, committing, or pushing.
- Create a commit only when the user asks.

## Limits

- **NEVER** edit or test under `dist/`. Change the origin tree (`Makefile`, `dss/`, service directories). Leave `dist/` empty unless the user asks for a new export.
- Do not commit `.env` files or `traefik/certs/*.{crt,key}`.
- Do not run `make remove-all`, `make prune`, or `make remove-config` unless the user asks. They delete data or env files.

## More docs

- Commands: `docs/usage.md`
- Configuration: `docs/configuration.md`
- Networks: `docs/network-segmentation.md`
- Service URLs: `make info` and `docs/services.md`
- Troubleshooting: `docs/troubleshooting.md`
