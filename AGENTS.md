# AGENTS.md

Entry point for agents and contributors. Rules live in `docs/dev/`. Each rule there names the tool that enforces it, or says it is review only.

## Project

Local Docker Compose infrastructure for development (databases, cache, auth, CI, observability). Each service is its own Compose project, started from the root Makefile via `python -m dss.cli.service` (run through `uv`). Web UIs are reached through Traefik at `https://*.dss.localhost`.

## Rules

| Topic                                      | Doc                                                          |
| ------------------------------------------ | ------------------------------------------------------------ |
| `dss` layers, lint/type rules, new modules | [docs/dev/python-layout.md](docs/dev/python-layout.md)       |
| Shell scripts                              | [docs/dev/shell-scripts.md](docs/dev/shell-scripts.md)       |
| `make check`, limits, goldens, git hooks   | [docs/dev/quality-gate.md](docs/dev/quality-gate.md)         |
| Compose layout, Traefik, catalog, backends | [docs/dev/adding-a-service.md](docs/dev/adding-a-service.md) |

Write files in this repo in English (README, `docs/`, comments, commits, `.env.example`).

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
make hooks                              # install prek git hooks
```

Every target that runs Python needs `uv`. The Makefile stops with an install hint when it is missing. `make tui` and `make package` also need a TTY.

## Structure

- `dss/` — Python package: `core` (config, catalog, env, secrets; stdlib only), `cli` (make entry points), `package` (`make package` exporter + wizard), `tui` (Textual dashboard)
- `tools/` — dev tooling (`format_repo.py`, `check_file_size.py`)
- `scripts/` — shell scripts called by Makefile recipes
- `<service>/` — that service's `docker-compose.yml` and `.env.example`
- `docker-compose.shared.yml` — external networks `traefik_proxy`, `backend_net`, `data_net`
- `docs/` — usage, configuration, networking, troubleshooting; `docs/dev/` — contributor rules
- `dist/` — export from `make package`; gitignored

## Gotchas

- `depends_on` does not cross Compose projects. `make up service=<name>` must start that service's `dependency_queue` and wait until each backend container is `running` and, when a healthcheck exists, `healthy`. A created container is not ready.
- `make up` without `service=` opens a menu. Pass `service=<name>`.
- `make setup` prompts before writing `.env` files and certificates. Skip it when there is no TTY.
- Root `.env` must exist before `make up`. Create it with `make setup`.
- Setup rejects the legacy password `Password102!`.
- `dss/core/config.py` is copied into exports, so editing it changes the export goldens. Run `make test-update` and review the diff.

## Workflow

- After Compose, shell, `dss/`, `tools/`, or `tests/` edits, run `make check`.
- Ask before adding dependencies, committing, or pushing. Create a commit only when the user asks.

## Limits

- **NEVER** edit or test under `dist/`. Change the origin tree (`Makefile`, `dss/`, service directories). Leave `dist/` empty unless the user asks for a new export.
- Do not commit `.env` files or `traefik/certs/*.{crt,key}`.
- Do not run `make remove-all`, `make prune`, or `make remove-config` unless the user asks. They delete data or env files.
- Do not lower a quality limit (complexity, coverage floor, 300-line file size) to pass a check.

## More docs

- Commands: `docs/usage.md`
- Configuration: `docs/configuration.md`
- Networks: `docs/network-segmentation.md`
- Service URLs: `make info` and `docs/services.md`
- Troubleshooting: `docs/troubleshooting.md`
