# Hasura GraphQL Engine

Hasura provides an instant GraphQL API over the shared Postgres 16 service. Metadata and the default data source both use the `hasura` database. The Console and GraphQL endpoint are available through Traefik TLS at `hasura.dss.localhost`.

Upstream: [hasura/graphql-engine](https://github.com/hasura/graphql-engine).

## Quick Start

```sh
# From repo root
make setup                    # Initializes hasura/.env if needed
make up service=postgres      # Database dependency
make up service=traefik       # Optional: reverse proxy / TLS
make up service=hasura
```

| Resource         | URL                                       | Default Credentials            |
| ---------------- | ----------------------------------------- | ------------------------------ |
| Console (TLS)    | `https://hasura.dss.localhost/console`    | Admin secret: `Password102!`   |
| GraphQL endpoint | `https://hasura.dss.localhost/v1/graphql` | Header `x-hasura-admin-secret` |

## Database Dependency

Hasura stores metadata (and uses `PG_DATABASE_URL` as the default Postgres source) in the `hasura` database inside the shared `postgres` container (`postgres:5432`).

- **New installation**: `postgres/bin/init.sh` automatically creates `CREATE DATABASE hasura;` on first startup.
- **Pre-existing volume**: If your `postgres` data volume already exists, run:
  ```sh
  docker exec -it postgres psql -U postgres -c 'CREATE DATABASE hasura;'
  ```

Connection defaults (override in `hasura/.env`):

```text
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=Password102!
POSTGRES_DB=hasura
```

## Configuration Notes

- **Image**: `hasura/graphql-engine` pinned via `HASURA_VERSION` (default `v2.50.3`).
- **Console / dev mode**: enabled by default for local use; set `HASURA_GRAPHQL_ENABLE_CONSOLE=false` and `HASURA_GRAPHQL_DEV_MODE=false` for stricter setups.
- **Admin secret**: `HASURA_GRAPHQL_ADMIN_SECRET` (synced by `make setup` shared-password flow).

## Useful Commands

```sh
make logs service=hasura
make health service=hasura
make restart service=hasura
make down service=hasura
```
