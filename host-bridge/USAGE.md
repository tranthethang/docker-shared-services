# host-bridge

Central HAProxy TCP bridge for the default DSS dev profile. HTTP(S) stays on **Caddy** (docker-shared-services-proxy) → **Traefik**; this stack only forwards the eleven host aliases on `127.0.0.1`.

## Startup order

1. Start the backends you need (`make up service=postgres`, `make up service=redis`, and so on).
1. Start the bridge: `make up service=host-bridge`.

Until the bridge is running, `localhost:<alias>` does not reach containers once per-service `ports:` are removed from those backends.

## Host aliases (default profile)

See the port table in [host-bridge-haproxy brainstorm notes](../.agent-relay/brainstorms/20261105-host-bridge-haproxy/notes.md#default-profile-11-listens-on-127001).

| Host alias | Upstream container | Container port |
| ---------- | ------------------ | -------------- |
| 5432       | postgres           | 5432           |
| 5433       | pgvector           | 5432           |
| 5434       | supabase-db        | 5432           |
| 3306       | mysql8             | 3306           |
| 3307       | mariadb            | 3306           |
| 27017      | mongodb            | 27017          |
| 6379       | redis              | 6379           |
| 11211      | memcached          | 11211          |
| 5672       | rabbitmq           | 5672           |
| 9092       | kafka              | 9092           |
| 1025       | mailpit            | 1025           |

Published host ports follow the root `.env` variables (`POSTGRES16_PORT`, `REDIS_PORT`, …) with the same defaults as today.

## SANDBOX_NAME

When `SANDBOX_NAME` is set in the root `.env`, upstream DNS names are `${SANDBOX_NAME}-<container>` (for example `dev-postgres`). The bridge substitutes `__UPSTREAM_PREFIX__` in `haproxy.cfg` at container start from that prefix.

## Extended profile

The default stack mounts only `haproxy.cfg` (eleven rules). Optional rules for MinIO S3, Loki, OTLP, Temporal, Centrifugo, Gotenberg, LibreOffice UNO, Verdaccio, Gitea SSH, and the Jenkins agent live in `haproxy.extended.cfg`. See the [extended overlay section](../.agent-relay/brainstorms/20261105-host-bridge-haproxy/notes.md#extended-overlay-optional-not-shipped-as-default) in the brainstorm notes.

To enable the overlay without changing the default `make up service=host-bridge` path:

1. Create a local override, for example `host-bridge/docker-compose.extended.yml`, that adds port publishes for the extended host aliases and mounts `haproxy.extended.cfg`.
1. Change the bridge command to merge configs before `sed`, for example `cat /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.extended.cfg > /tmp/haproxy.merged.cfg` then substitute `__UPSTREAM_PREFIX__` on that file.
1. Start with `docker compose -f docker-compose.shared.yml -f host-bridge/docker-compose.yml -f host-bridge/docker-compose.extended.yml up -d` (adjust paths to match your override).

Keep extended services off the default path so most developers only pay for eleven listens.

## Kafka note

Kafka advertises `EXTERNAL://localhost:9092`. Clients on the Mac still use `127.0.0.1:9092` through this bridge; if a backend is down, HAProxy refuses the connection until that upstream is up.
