# Docker Shared Services

![Docker Shared Services](assets/repo.png)

Local Docker Compose stack for common infra: databases, cache, messaging, CI/CD, auth, storage, and observability. Managed with a `Makefile` + scripts in `bin/`.

**macOS / Linux only.** Windows is unsupported (WSL2 may work, untested).

> **Local development only.** Host ports bind to `127.0.0.1`. Do not expose this stack to the internet.

## Quick start

```bash
# 1) Networks, .env files, shared password, optional TLS certs
make setup
# Keep the classic password instead of a random one:
#   make setup password='Password102!'

# 2) Start what you need
make up                        # interactive
make up service=postgres       # one service (folder name)

# 3) Check
make ps
make info                      # URLs / ports
```

Access via Traefik: `https://<service>.dss.localhost` (needs `make cert` / mkcert once).
Browser UIs are available only through their domain names; UI ports are not published to the host.

## Shared password

`make setup` writes **one** password into all service password fields (Postgres, Redis, MinIO, Grafana, …). Unique secrets (Garage, Woodpecker agent, Zitadel masterkey, oauth2-proxy cookie secret) stay separate.

| Goal                   | Command                                         |
| ---------------------- | ----------------------------------------------- |
| Random shared password | `make setup`                                    |
| Use `Password102!`     | `make setup password='Password102!'`            |
| Same via env           | `DSS_SHARED_PASSWORD='Password102!' make setup` |
| Rotate later           | `make passwords password='NewPass' force=1`     |

Value is stored as `DSS_SHARED_PASSWORD` in the root `.env`.

## Common commands

| Command                                 | What it does                                                   |
| --------------------------------------- | -------------------------------------------------------------- |
| `make setup`                            | Networks, `.env`, shared password, Dozzle user, optional certs |
| `make passwords`                        | Apply / rotate the shared password                             |
| `make up` / `down` / `stop` / `restart` | Lifecycle (`service=<folder>` optional)                        |
| `make manage`                           | Interactive multi-select start/stop                            |
| `make logs` / `ps` / `health` / `info`  | Observe                                                        |
| `make cert`                             | TLS for `*.dss.localhost` (requires mkcert)                    |
| `make validate`                         | Validate all compose files                                     |
| `make remove-config`                    | Delete generated `.env` files (confirm)                        |
| `make remove-all`                       | **Wipe containers + volumes** (confirm)                        |

```bash
make up service=redis
make logs service=gitea
make restart service=postgres
```

## What’s included

| Area        | Examples                                                                                        |
| ----------- | ----------------------------------------------------------------------------------------------- |
| Data        | Postgres 16, PgVector 17, MySQL, MariaDB, MongoDB, Redis, Memcached, ChromaDB, Qdrant           |
| Messaging   | RabbitMQ, Kafka, Centrifugo                                                                     |
| Auth / apps | Zitadel, oauth2-proxy (`auth.dss.localhost`), Supabase, Gitea, n8n, Appsmith, Hindsight, Hasura |
| CI / ops    | Jenkins, Concourse, Woodpecker, SonarQube, Portainer, Dockge, Dozzle                            |
| Storage     | MinIO, Garage                                                                                   |
| Edge / obs  | Traefik, OTel (Collector + Loki + Promtail + Grafana)                                           |

Full catalog: [docs/services.md](docs/services.md).

## Layout

```
docker-compose.shared.yml   # networks: infra_shared, dev_tools
Makefile                    # day-to-day commands
bin/                        # env + service managers
<service>/                  # docker-compose.yml + .env.example
docs/                       # deeper guides
```

## Opt-in UI authentication

Selected Traefik UIs can require Zitadel login via `oauth2-proxy` (`https://auth.dss.localhost`). Auth is **off by default**.

1. Start Traefik + Zitadel + oauth2-proxy (register a Zitadel Web app — see [oauth2-proxy/README.md](oauth2-proxy/README.md)).
1. In a candidate service `.env` set `AUTH_ENABLED=true` and `AUTH_MIDDLEWARE=auth-default`, then restart that service.
1. Candidates (remain disabled until you opt in): Mermaid Live Editor, Temporal UI, ChromaDB, Qdrant, Kafka UI.

For Mermaid Live Editor, `AUTH_ENABLED=true` alone is not sufficient; make sure `AUTH_MIDDLEWARE=auth-default` is set instead of the default `auth-none`.

Details: [docs/configuration.md](docs/configuration.md#opt-in-zitadel-ui-authentication).

## Docs

- [Services & access](docs/services.md)
- [Configuration & networking](docs/configuration.md)
- [Usage](docs/usage.md)
- [Troubleshooting](docs/troubleshooting.md)

## Requirements

Docker Engine 20.10+, Compose v2+, Make, Python 3. Optional: [mkcert](https://github.com/FiloSottile/mkcert) for local HTTPS.

## License

See [LICENSE](LICENSE). Issues and PRs welcome.
