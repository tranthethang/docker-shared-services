# Configuration & Networking Guide

> Guide on how to configure environment variables, change default passwords, customize ports, adjust resource limits, set up internal Docker networks, and generate SSL/TLS certificates for Traefik.

______________________________________________________________________

## ⚙️ Configuration

### Environment Files

Each service has a `.env.example` file. Copy and customize:

```bash
cp pgvector/.env.example pgvector/.env
# Edit pgvector/.env with your values
```

### Shared password (recommended)

`make setup` applies **one** shared password to every service password field that
still has the repo placeholder (`Password102!` or empty). Unique secrets (Garage,
Woodpecker agent, Zitadel masterkey) are generated separately.

```bash
# Generate a random shared password and write it into all service .env files
make setup

# Keep using the classic local default
make setup password='Password102!'
# equivalent:
DSS_SHARED_PASSWORD='Password102!' make setup

# Rotate later (overwrites even non-placeholder values)
make passwords password='MyNewSharedPass' force=1
```

The chosen value is stored as `DSS_SHARED_PASSWORD` in the root `.env` and copied
into each service’s password variables (Postgres, Redis, MinIO, Grafana, …).

### Change a single service password

```bash
# Edit that service's .env only (won't be overwritten unless you pass force=1)
POSTGRES_PASSWORD=your_strong_password
MYSQL_ROOT_PASSWORD=your_strong_password
MONGO_ROOT_PASSWORD=your_strong_password
```

### Change Ports

```bash
# Edit service .env file
POSTGRES_PORT=5555          # pgvector's own port (default is already 5433,
                             # chosen so it never clashes with Postgres 16 on 5432)
MYSQL_PORT=3307              # Instead of 3306
```

### Resource Limits

```env
POSTGRES_CPUS_LIMIT=2
POSTGRES_MEMORY_LIMIT=2G
POSTGRES_CPUS_RESERVED=1
POSTGRES_MEMORY_RESERVED=1G
```

### Enable/Disable Services

Edit `start-services.sh` or `Makefile` and comment out unwanted services.

______________________________________________________________________

## 🌐 Network Configuration

Services use two **external** bridge networks (created by `make setup` if missing). Docker does not allow two networks to share the same CIDR, so both use adjacent `/16` blocks in `10.0.0.0/8`:

| Network        | Subnet        | Role                                                                         |
| :------------- | :------------ | :--------------------------------------------------------------------------- |
| `infra_shared` | `10.0.0.0/16` | Primary stack, Traefik discovery (`--providers.docker.network=infra_shared`) |
| `dev_tools`    | `10.1.0.0/16` | Legacy or external compose projects that attach to `dev_tools`               |

Most service containers join **both** networks so they can reach Traefik on `infra_shared` and legacy workloads on `dev_tools`.

Services communicate using container names on the network where both endpoints are attached:

```bash
# Postgres 16 - the default shared DB backend (gitea, jenkins, concourse,
# sonarqube, zitadel, inngest, temporal, bugsink, hasura all connect here by default)
postgres://postgres:Password102!@postgres:5432/mydb

# PgVector - Postgres 17 + vector extension; shared backend for Hindsight
# (and available for your own workloads). Port 5432 inside the network,
# host-mapped to 5433.
postgres://postgres:Password102!@pgvector:5432/mydb

# Redis
redis://:Password102!@redis:6379

# RabbitMQ (default user is admin; password = shared password)
amqp://admin:<DSS_SHARED_PASSWORD>@rabbitmq:5672

# Service-to-service (default shared Postgres backend)
POSTGRES_HOST=postgres
REDIS_HOST=redis
RABBITMQ_HOST=rabbitmq
```

### Network Inspection

```bash
docker network ls                            # List networks
docker network inspect infra_shared             # Inspect primary network
docker network inspect dev_tools                # Inspect legacy network
docker network inspect infra_shared | grep -A 20 "Containers"  # List attached containers
docker exec [container] ping [other_container]  # Test connectivity
```

______________________________________________________________________

## Opt-in Zitadel UI authentication

Browser UIs can sit behind a shared `oauth2-proxy` gateway that authenticates users with Zitadel. Authentication is **opt-in and disabled by default**.

### Rollout

1. `make setup` (creates `oauth2-proxy/.env` and fills `OAUTH2_PROXY_COOKIE_SECRET` when empty).
1. Start dependencies: `make up service=traefik`, `make up service=postgres`, `make up service=zitadel`.
1. Register a confidential Web application in Zitadel Console with redirect URI `https://auth.dss.localhost/oauth2/callback`. Put the client id/secret into `oauth2-proxy/.env` (never auto-generated).
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

Middleware names: `auth-none` (public default), `auth-default` (any authenticated user), `auth-admin` (extension point for stricter policy later). Do **not** protect Zitadel itself.

### Status and lifecycle

```bash
make info                              # Lists gateway URL + opt-in guidance
python bin/env_manager.py summary      # Per-UI AUTH gateway on/off
make up service=oauth2-proxy
make logs service=oauth2-proxy
make restart service=mermaid-live-editor
```

Full gateway details: [oauth2-proxy/README.md](../oauth2-proxy/README.md).

______________________________________________________________________

## 🔒 SSL/TLS Certificate Setup (Traefik)

Traefik requires SSL/TLS certificates for HTTPS support. The easiest way is using `mkcert`.

Public Traefik hostnames use the `*.dss.localhost` pattern (for example `https://mailpit.dss.localhost`). A bare `*.localhost` wildcard is **not** accepted by Chrome/OpenSSL for names like `mailpit.localhost`, which is why services are under `dss.localhost`.

Nested app hosts (one extra label) need an extra wildcard SAN — `make cert` also issues `*.tts.dss.localhost` (for `api.tts.dss.localhost`, `proxy.tts.dss.localhost`), plus `*.minio.dss.localhost` and `*.garage.dss.localhost`. Re-run `make cert` and restart Traefik after changing SANs.

### Option 1: Using Makefile (Recommended)

```bash
# 1. Install mkcert (and trust the local CA)
# macOS: brew install mkcert nss && mkcert -install
# Linux: Follow mkcert installation guide, then mkcert -install

# 2. Run the make command
make cert
```

### Option 2: Manual Setup

```bash
mkdir -p traefik/certs

openssl req -x509 -newkey rsa:4096 -keyout traefik/certs/server.key \
  -out traefik/certs/server.crt -days 365 -nodes \
  -subj "/CN=localhost"
```

### Important Notes

- **Certificate files are in `.gitignore`** - They are NOT committed to the repository.
- **Generate fresh certificates** for each environment (development, staging, production).
- Certificates are located in: `traefik/certs/server.crt` and `traefik/certs/server.key`.
- Update certificate validity period in the mkcert command as needed (default: 2 years).

### Verify Certificates

```bash
# Check certificate details
openssl x509 -in traefik/certs/server.crt -text -noout

# Check expiration
openssl x509 -in traefik/certs/server.crt -noout -dates
```

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Commands & Operations Guide](usage.md)
- [Troubleshooting & Support](troubleshooting.md)
