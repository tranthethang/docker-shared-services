# Zitadel Central IdP

Zitadel is the centralized Identity Provider (IdP) for the shared services stack. It connects to the shared Postgres service and routes through Traefik using h2c (gRPC/HTTP2 cleartext).

## Quick Start

```sh
# From repo root
make setup                    # Initializes zitadel/.env if needed
make up service=postgres      # Database dependency
make up service=traefik       # Reverse proxy / TLS termination
make up service=zitadel       # Starts Zitadel API and Login UI
```

| Resource         | URL                                         | Default Credentials                                                            |
| ---------------- | ------------------------------------------- | ------------------------------------------------------------------------------ |
| Console UI       | `https://zitadel.dss.localhost/ui/console`  | User: `zitadel-admin@zitadel.zitadel.dss.localhost` / Password: `Password102!` |
| Login UI (v2)    | `https://zitadel.dss.localhost/ui/v2/login` | Served by `zitadel-login`                                                      |
| Direct host port | `http://localhost:8180`                     | Same instance (no Traefik TLS)                                                 |

## Database Dependency

Zitadel stores its schema in the `zitadel` database inside the shared `postgres` container (`postgres:5432`).

- **New installation**: `postgres/bin/init.sh` automatically creates `CREATE DATABASE zitadel;` on first startup.
- **Pre-existing volume**: If your `postgres` data volume already exists, execute the following one-shot command:
  ```sh
  docker exec -it postgres psql -U postgres -c 'CREATE DATABASE zitadel;'
  ```

## Architecture & Traefik Routing

- **Traefik TLS**: Traefik terminates TLS for `zitadel.dss.localhost`.
- **API Upstream (h2c)**: Non-login paths go to container port `8080` with scheme `h2c` (required for Console / gRPC).
- **Login UI Upstream**: `/ui/v2/login` (and `/`) go to `zitadel-login` on port `3000`.
- **Images**: API and Login must share the same `ZITADEL_VERSION` (default `v4.16.3`).

## Optional Caching (Redis)

1. Start shared Redis: `make up service=redis`
1. In `zitadel/.env`, set `ZITADEL_CACHES_CONNECTORS_REDIS_ENABLED=true` and uncomment the three `ZITADEL_CACHES_*_CONNECTOR=redis` lines.
1. Restart: `make restart service=zitadel`
