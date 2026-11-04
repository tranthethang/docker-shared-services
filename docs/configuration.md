# Configuration & Networking Guide

> Guide on how to configure environment variables, change default passwords, customize ports, adjust resource limits, set up internal Docker networks, and terminate HTTPS with Caddy at the edge.

______________________________________________________________________

## ⚙️ Configuration

### Environment Files

Each service has a `.env.example` file. Copy and customize:

```bash
cp pgvector/.env.example pgvector/.env
# Edit pgvector/.env with your values
```

### Domain

`DOMAIN` in the root `.env` sets the base domain of every DSS hostname. The default is `dss.localhost`, so Adminer is at `https://adminer.dss.localhost`.

```env
# root .env
DOMAIN=dev.example.test
```

`make up` passes the root `.env` to Compose first and the service `.env` second. A value in a service `.env` overrides the root value. Traefik labels, the Traefik default rule, the per-service URLs, and `make info` all follow `DOMAIN`.

Per-service host and URL variables are empty in the `.env.example` files. Each one has a `# Default:` comment that shows the value built from `DOMAIN`, for example `ZITADEL_HOSTNAME` defaults to `zitadel.${DOMAIN}`. Set one only to give that service a different host.

An existing `.env` keeps its explicit host values, such as `ZITADEL_HOSTNAME=zitadel.dss.localhost` or `GITEA_ROOT_URL=https://gitea.dss.localhost/`. Clear those values to follow `DOMAIN`. `DOMAIN_NAME` is no longer read; move a custom value to `DOMAIN`.

Some files are not interpolated by Compose and keep `dss.localhost`: `garage/config/garage.toml`. Edit that file by hand for another domain. The smoke scripts `otel/test-otel.sh` and `hindsight/smoke-test.sh` read `DOMAIN` from the shell environment, so export it before you run them. The Caddy certificate in the proxy repo must also cover the new domain.

### Several stacks on one host

`DSS_NAME` and `DSS_SUBNET_BASE` in the root `.env` let several DSS stacks share one Docker host. Both are optional. With `DSS_NAME` empty, every name stays as before.

| Item                 | Default (`DSS_NAME` empty) | With `DSS_NAME=projb`  |
| -------------------- | -------------------------- | ---------------------- |
| Compose project      | `postgres`                 | `projb-postgres`       |
| Container            | `postgres`                 | `projb-postgres`       |
| Shared networks      | `data_net`                 | `projb_data_net`       |
| Traefik socket net   | `traefik_docker`           | `projb_traefik_docker` |
| Traefik router label | `dss.stack=dss`            | `dss.stack=projb`      |

`DSS_NAME` accepts lowercase letters, digits, `_`, and `-`, and must start with a letter or digit. `DSS_SUBNET_BASE` (0 to 253, default 0) sets the subnets `10.<base>.0.0/16`, `10.<base+1>.0.0/16`, and `10.<base+2>.0.0/16` for `traefik_proxy`, `backend_net`, and `data_net`. Services still reach each other by Compose service name, such as `postgres`, in every stack.

Example for a second stack:

```env
# root .env of the second checkout
DSS_NAME=projb
DSS_SUBNET_BASE=10
```

`make setup` then creates `projb_traefik_proxy` (`10.10.0.0/16`), `projb_backend_net` (`10.11.0.0/16`), and `projb_data_net` (`10.12.0.0/16`).

- Give each stack its own checkout or its own root `.env`, so each reads its own `DSS_NAME`.
- Subnets must not overlap. Give each stack a `DSS_SUBNET_BASE` at least 3 higher than the previous one.
- Each Traefik only routes containers with its own `dss.stack` label, so two stacks never list each other's routers.
- Data volumes are not shared or migrated between stacks.
- Set the same `DSS_NAME` in the root `.env` before the first `make up`. Changing it later creates new containers and networks next to the old ones.

### Shared password (recommended)

`make setup` applies **one** shared password to every service password field that
is still empty (or holds the legacy `Password102!` default from an older `.env`). Unique secrets are
generated separately, only when the value is empty: Garage, LiteLLM, the oauth2-proxy cookie secret,
the Woodpecker agent secret, the Zitadel masterkey, the Bugsink secret key, the Inngest event and
signing keys (16 hex characters), and the Supabase secrets. Supabase `ANON_KEY` and `SERVICE_ROLE_KEY`
are HS256 JWTs signed with the generated `JWT_SECRET`.

An older `.env` may still hold a former example value such as `MasterkeyNeedsToHave32Characters` or
the Supabase demo keys. `make setup` warns about it and leaves it unchanged, because the Zitadel
masterkey and `REALTIME_DB_ENC_KEY` encrypt existing data. Replace those values yourself before the
first start, or after resetting that service's data.

```bash
# Generate a random shared password and write it into all service .env files
make setup

# Or choose a secure shared password
make setup password='your-secure-password'
# equivalent:
DSS_SHARED_PASSWORD='your-secure-password' make setup

# Rotate later (overwrites even non-placeholder values)
make passwords password='MyNewSharedPass' force=1
```

The chosen value is stored as `DSS_SHARED_PASSWORD` in the root `.env` and copied
into each service’s password variables (Postgres, Redis, MinIO, Grafana, …).
Run `make setup` before direct `docker compose up` commands so the required `.env` files and credentials exist.
The Traefik dashboard uses `admin` and this shared password at `https://traefik.dss.localhost/dashboard/`.

### Change a single service password

```bash
# Edit that service's .env only (won't be overwritten unless you pass force=1)
POSTGRES16_PASSWORD=your_strong_password
PGVECTOR_PASSWORD=your_strong_password
MYSQL_ROOT_PASSWORD=your_strong_password
MONGO_ROOT_PASSWORD=your_strong_password
```

### Change Ports

```bash
# Edit service .env file
PGVECTOR_PORT=5555          # pgvector's host port (default is already 5433,
                             # chosen so it never clashes with Postgres 16 on 5432)
MYSQL_PORT=3307              # Instead of 3306
```

### Resource Limits

```env
PGVECTOR_CPUS_LIMIT=2
PGVECTOR_MEMORY_LIMIT=2G
PGVECTOR_CPUS_RESERVED=1
PGVECTOR_MEMORY_RESERVED=1G
```

### Enable/Disable Services

Edit `start-services.sh` or `Makefile` and comment out unwanted services.

______________________________________________________________________

## 🌐 Network Configuration

Services use three **external** bridge networks (created by `make setup` if missing), with separate `/16` blocks in `10.0.0.0/8`:

| Network         | Subnet        | Role                                  |
| :-------------- | :------------ | :------------------------------------ |
| `traefik_proxy` | `10.0.0.0/16` | Traefik and routed HTTP services      |
| `backend_net`   | `10.1.0.0/16` | Application and worker communication  |
| `data_net`      | `10.2.0.0/16` | Databases, caches, and direct clients |

See [network segmentation](network-segmentation.md) for each container's network attachments.

Services communicate using container names on the network where both endpoints are attached:

```bash
# Postgres 16 - the default shared DB backend (gitea, jenkins, concourse,
# sonarqube, zitadel, inngest, temporal, bugsink, hasura all connect here by default)
postgres://postgres:<DSS_SHARED_PASSWORD>@postgres:5432/mydb

# PgVector - Postgres 17 + vector extension; shared backend for Hindsight
# (and available for your own workloads). Port 5432 inside the network,
# host-mapped to 5433.
postgres://postgres:<DSS_SHARED_PASSWORD>@pgvector:5432/mydb

# Redis
redis://:<DSS_SHARED_PASSWORD>@redis:6379

# RabbitMQ (default user is admin; password = shared password)
amqp://admin:<DSS_SHARED_PASSWORD>@rabbitmq:5672

# Service-to-service (default shared Postgres backend)
POSTGRES16_HOST=postgres
REDIS_HOST=redis
RABBITMQ_HOST=rabbitmq
```

### Network Inspection

```bash
docker network ls                               # List networks
docker network inspect traefik_proxy            # Inspect ingress network
docker network inspect backend_net              # Inspect application network
docker network inspect data_net                 # Inspect data network
docker exec [container] ping [other_container]  # Test connectivity
```

______________________________________________________________________

## Opt-in OIDC UI authentication

Browser UIs can sit behind a shared `oauth2-proxy` gateway that authenticates users with any OIDC issuer. Authentication is **opt-in and disabled by default**.

### Rollout

1. `make setup` (creates `oauth2-proxy/.env` and fills `OAUTH2_PROXY_COOKIE_SECRET` when empty). General setup validation only requires the cookie secret; empty `OAUTH2_PROXY_CLIENT_ID` / `OAUTH2_PROXY_CLIENT_SECRET` are expected until you opt in.
1. Start Traefik: `make up service=traefik`.
1. Register a confidential client with your OIDC provider and allow redirect URI `https://auth.dss.localhost/oauth2/callback`. Set `OAUTH2_PROXY_OIDC_ISSUER_URL` to the issuer base URL (origin plus path, not the well-known URL), and set the client id/secret in `oauth2-proxy/.env`. For a public issuer, leave `OAUTH2_PROXY_OIDC_ISSUER_HOST` empty. For a local issuer reached through this machine's Traefik, set it to the issuer hostname only, for example `idp.dss.localhost`.
1. The client id/secret are manual prerequisites for oauth2-proxy and are never auto-generated. Until both values are set, `make manage` and `make tui` show `oauth2-proxy` as a label and will not start it. `make up service=oauth2-proxy` exits with the same reason.
1. `make up service=oauth2-proxy`.
1. To protect a UI, edit that service’s `.env`:

```env
AUTH_ENABLED=true
AUTH_MIDDLEWARE=auth-default
```

Then `make restart service=<folder>`. Set `AUTH_MIDDLEWARE=auth-none` (and `AUTH_ENABLED=false`) to return to public access.

### Initial candidates (default: off)

| Folder / UI           | Traefik host             | Notes                                      |
| --------------------- | ------------------------ | ------------------------------------------ |
| `mermaid-live-editor` | `mermaid.dss.localhost`  | Browser editor; WebSockets go through auth |
| `temporal` (UI only)  | `temporal.dss.localhost` | gRPC `:7233` is not gated                  |
| `chromadb`            | `chromadb.dss.localhost` | Enabling breaks non-browser API on Traefik |
| `qdrant`              | `qdrant.dss.localhost`   | Prefer native `QDRANT_API_KEY` for APIs    |
| `kafka` (Kafka UI)    | `kafka-ui.dss.localhost` | UI only                                    |

Middleware names: `auth-none` (public default), `auth-default` (any authenticated user), `auth-admin` (extension point for stricter policy later). Do **not** protect the OIDC issuer itself.

### Status and lifecycle

```bash
make info                              # Lists gateway URL + opt-in guidance
uv run python -m dss.cli.env summary   # Per-UI AUTH gateway on/off
make up service=oauth2-proxy
make logs service=oauth2-proxy
make restart service=mermaid-live-editor
```

Full gateway details: [oauth2-proxy/README.md](../oauth2-proxy/README.md).

______________________________________________________________________

## 🔒 HTTPS edge (Caddy)

TLS and host ports **80/443** live in the companion repo [docker-shared-services-proxy](https://github.com/tranthethang/docker-shared-services-proxy). Traefik in this repo listens on **HTTP port 80** inside `traefik_proxy` only; it does not mount server certificates or publish 80/443 on the Docker host by default. See [Proxy contract](#proxy-contract) for the optional published port.

Public hostnames still use `*.dss.localhost` (for example `https://mailpit.dss.localhost`). A bare `*.localhost` wildcard is **not** accepted by Chrome/OpenSSL for names like `mailpit.localhost`, which is why services are under `dss.localhost`.

Nested app hosts (one extra label) need extra wildcard SANs on the Caddy certificate — the proxy repo `make cert` script issues `*.tts.dss.localhost`, `*.minio.dss.localhost`, and `*.garage.dss.localhost` in addition to `*.dss.localhost`. Re-run `make cert` in the proxy repo and restart Caddy after changing SANs.

### Startup order

```bash
# 1. This repo — networks and env
make setup

# 2. docker-shared-services-proxy — TLS edge
make setup && make cert && make up

# 3. This repo — internal router and services
make up service=traefik
make up service=<name>
```

### Generate certificates (proxy repo)

```bash
# Install mkcert and trust the local CA once
# macOS: brew install mkcert nss && mkcert -install

cd ../docker-shared-services-proxy   # or your clone path
make cert
```

Certificate files are written to `caddy/certs/server.crt` and `server.key` in the proxy repo. They are gitignored and are **not** committed.

### Verify certificates

```bash
openssl x509 -in caddy/certs/server.crt -text -noout    # run from proxy repo
openssl x509 -in caddy/certs/server.crt -noout -dates
```

Do not browse Traefik directly on host ports; use `https://traefik.dss.localhost/dashboard/` through Caddy.

______________________________________________________________________

## Proxy contract

Any HTTPS proxy can sit in front of Traefik, local Caddy or a remote proxy. The proxy must follow these rules:

- Traefik speaks HTTP on port 80 only. The proxy terminates TLS.
- The proxy sends the original `Host` header and `X-Forwarded-Proto: https`.
- The proxy address is inside `TRAEFIK_TRUSTED_IPS`. Traefik ignores `X-Forwarded-*` headers from other addresses. The default is `10.0.0.0/8,172.16.0.0/12,192.168.0.0/16`.
- A remote proxy reaches Traefik through `TRAEFIK_BIND` and `TRAEFIK_HTTP_PORT` in `traefik/.env`. When `TRAEFIK_HTTP_PORT` is set, `make up service=traefik` adds `traefik/docker-compose.publish.yml` and publishes `${TRAEFIK_BIND}:${TRAEFIK_HTTP_PORT}:80`. When it is empty, Traefik publishes no port.
- `TRAEFIK_BIND` must be a private address. With private ranges in `TRAEFIK_TRUSTED_IPS`, any host in the VPC can forge forwarded headers. Narrow `TRAEFIK_TRUSTED_IPS` to the proxy address when other hosts share that network.

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Commands & Operations Guide](usage.md)
- [Troubleshooting & Support](troubleshooting.md)
