# host-bridge

Central HAProxy TCP bridge for the default DSS dev profile. HTTP(S) stays on **Caddy** (docker-shared-services-proxy) → **Traefik**; this stack only forwards the eleven host aliases on `127.0.0.1`.

## Startup order

1. Start the backends you need (`make up service=postgres`, `make up service=redis`, and so on).
2. Start the bridge: `make up service=host-bridge` (after task T3 registers the service in the catalog).

Until the bridge is running, `localhost:<alias>` does not reach containers once per-service `ports:` are removed from those backends.

## Host aliases (default profile)

See the port table in [host-bridge-haproxy brainstorm notes](../.agent-relay/brainstorms/20261105-host-bridge-haproxy/notes.md#default-profile-11-listens-on-127001).

| Host alias | Upstream container | Container port |
| ---------- | ------------------ | -------------- |
| 5432 | postgres | 5432 |
| 5433 | pgvector | 5432 |
| 5434 | supabase-db | 5432 |
| 3306 | mysql8 | 3306 |
| 3307 | mariadb | 3306 |
| 27017 | mongodb | 27017 |
| 6379 | redis | 6379 |
| 11211 | memcached | 11211 |
| 5672 | rabbitmq | 5672 |
| 9092 | kafka | 9092 |
| 1025 | mailpit | 1025 |

Published host ports follow the root `.env` variables (`POSTGRES16_PORT`, `REDIS_PORT`, …) with the same defaults as today.

## SANDBOX_NAME

When `SANDBOX_NAME` is set in the root `.env`, upstream DNS names are `${SANDBOX_NAME}-<container>` (for example `dev-postgres`). The bridge substitutes `__UPSTREAM_PREFIX__` in `haproxy.cfg` at container start from that prefix.

## Extended profile

Optional TCP rules for MinIO, Loki, OTel, and other services live in `haproxy.extended.cfg` (added in a later task). The default `make up service=host-bridge` path mounts only `haproxy.cfg` (eleven rules).

## Kafka note

Kafka advertises `EXTERNAL://localhost:9092`. Clients on the Mac still use `127.0.0.1:9092` through this bridge; if a backend is down, HAProxy refuses the connection until that upstream is up.
