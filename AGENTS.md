# AGENTS.md

Entry point for agents and contributors. Rules live in `docs/dev/`. Each rule there names the tool that enforces it, or says it is review only.

## Project

Local Docker Compose infrastructure for development (databases, cache, auth, CI, observability). Each service is its own Compose project, started from the root Makefile through the Rust binary in `cli/` (`dss`, built with `cargo`). Web UIs are reached at `https://*.sandbox.localhost` by default (or your `DOMAIN`) through **Caddy** (proxy repo) into Traefik on `traefik_proxy`.

## Rules

| Topic                                      | Doc                                                          |
| ------------------------------------------ | ------------------------------------------------------------ |
| `cli/` modules, lint rules, new modules    | [docs/dev/rust-layout.md](docs/dev/rust-layout.md)           |
| `make check`, limits, Compose rules, hooks | [docs/dev/quality-gate.md](docs/dev/quality-gate.md)         |
| Compose layout, Traefik, catalog, backends | [docs/dev/adding-a-service.md](docs/dev/adding-a-service.md) |

Write files in this repo in English (README, `docs/`, comments, commits, `.env.example`).

## Commands

```bash
make setup                                      # networks + .env (interactive; needs a TTY)
make tui                                        # ratatui dashboard (interactive; needs a TTY)
make build                                      # build cli/target/release/dss
cli/target/release/dss up --service zitadel     # one service; queues its backends first
cli/target/release/dss down --service zitadel   # stop and remove that service's containers
cli/target/release/dss ps                       # status of running services
cli/target/release/dss health --service postgres # health for one service
cli/target/release/dss logs --service zitadel   # logs for one service
make check                                      # fmt, clippy, shellcheck, test, and Compose validate
make hooks                                      # install prek git hooks
```

Every `make` target and `dss` subcommand uses the `cli/` Rust binary, which `make build` (or `make setup`/`make tui`) builds with `cargo`. The Makefile stops with an install hint when `cargo` is missing. `make tui` and `make package` (without flags) need a TTY.

## Structure

- `cli/` — Rust crate `dss`: `config`, `stack`, `catalog`, `env` (secrets), `docker` (compose, readiness, state), `commands`, `tui` (ratatui dashboard), `package` (`make package` exporter + wizard). `cli/service_catalog.json` is the service catalog.
- `<service>/` — that service's `docker-compose.yml` and `.env.example`
- `docker-compose.shared.yml` — external networks `traefik_proxy`, `backend_net`, `data_net`
- `docs/` — usage, configuration, networking, troubleshooting; `docs/dev/` — contributor rules
- `dist/` — export from `make package`; gitignored

## Gotchas

- `depends_on` does not cross Compose projects. `dss up --service <name>` must start that service's `dependency_queue` and wait until each backend container is `running` and, when a healthcheck exists, `healthy`. A created container is not ready.
- `make setup` prompts before writing `.env` files. Skip it when there is no TTY (`cli/target/release/dss setup --yes`).
- Root `.env` must exist before `dss up` or `make tui` starts services. Create it with `make setup`.
- Setup rejects the legacy password `Password102!`.
- `cli/` is copied into exports. An export holds only the services you pick, listed in its `dss-package.json`.

## Workflow

- After Compose, `cli/`, or Makefile edits, run `make check`.
- Ask before adding dependencies, committing, or pushing. Create a commit only when the user asks.

## Limits

- **NEVER** edit or test under `dist/`. Change the origin tree (`Makefile`, `cli/`, service directories). Leave `dist/` empty unless the user asks for a new export.
- Do not commit `.env` files or TLS private keys. Local HTTPS certs live in the **docker-shared-services-proxy** repo under `caddy/certs/`.
- Do not run `cli/target/release/dss teardown`, `prune`, or `remove-config` unless the user asks. They delete data or env files.
- Do not lower a quality limit (clippy level, 300-line file size) to pass a check.

## More docs

- Commands: `docs/usage.md`
- Configuration: `docs/configuration.md`
- Networks: `docs/network-segmentation.md`
- Service URLs: `cli/target/release/dss info` and `docs/services.md`
- Troubleshooting: `docs/troubleshooting.md`
