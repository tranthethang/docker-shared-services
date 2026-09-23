# OTel — Logs-first observability stack

Local observability for Docker Shared Services: **OpenTelemetry Collector** as the default OTLP endpoint for apps, plus **Grafana + Loki + Promtail** for log storage and exploration.

Traces and metrics are **accepted** on the OTLP ports so instrumented apps work out of the box, then **dropped** (`nop` exporter) until Tempo / Prometheus are added (phase 2).

| Component      | Role                                     | Image (pinned via env)                         |
| -------------- | ---------------------------------------- | ---------------------------------------------- |
| OTel Collector | OTLP ingest (`4317` gRPC / `4318` HTTP)  | `otel/opentelemetry-collector-contrib:0.128.0` |
| Loki           | Log store (filesystem, 7-day retention)  | `grafana/loki` (`LOKI_VERSION`)                |
| Promtail       | Ships Docker container stdout → Loki     | `grafana/promtail` (`PROMTAIL_VERSION`)        |
| Grafana        | Explore UI (Loki datasource provisioned) | `grafana/grafana-oss` (`GRAFANA_VERSION`)      |

```
Apps (OTLP) ──► otel-collector ──► logs ──────────► Loki ──► Grafana
                             └── traces/metrics ─► nop
Docker stdout ─► Promtail ───────────────────────► Loki
```

**Related:** [Dozzle](../dozzle/) is for live container log tailing. Use Grafana/Loki for search, history, and app OTLP logs.

### Default Grafana login

| Field    | Value                         | Env override             |
| -------- | ----------------------------- | ------------------------ |
| URL      | https://grafana.dss.localhost | `GRAFANA_HOSTNAME`       |
| Username | `admin`                       | `GRAFANA_ADMIN_USER`     |
| Password | `Password102!`                | `GRAFANA_ADMIN_PASSWORD` |

Dev-only defaults (same pattern as other services in this repo). Change them in `otel/.env` or the root `.env` before exposing beyond localhost.

______________________________________________________________________

## Prerequisites

- Shared networks exist (`make setup` from the repo root creates `infra_shared` and `dev_tools`).
- **Traefik** running (`make up service=traefik`) for browser access via `*.dss.localhost` (same pattern as Zitadel).
- TLS certs for `*.dss.localhost` (`make cert` / `make setup`).

______________________________________________________________________

## Quick start

From the **repository root**:

```bash
# Ensure env files exist (also done by make setup)
cp otel/.env.example otel/.env

make up service=traefik   # if not already running
make up service=otel
make health service=otel
```

Or with Compose directly (same pattern the Makefile uses):

```bash
docker compose --project-directory otel \
  -f docker-compose.shared.yml \
  -f otel/docker-compose.yml \
  up -d
```

Smoke test (health checks + sample OTLP log):

```bash
./otel/test-otel.sh
```

Then open Grafana: [https://grafana.dss.localhost](https://grafana.dss.localhost)

- Username: `admin`
- Password: `Password102!`

______________________________________________________________________

## Access

Only **Grafana** is exposed through Traefik (like `https://zitadel.dss.localhost/...`). Loki, Promtail, and the Collector have no Traefik routers.

### Browser (Traefik)

| What    | URL                               | Default login                          |
| ------- | --------------------------------- | -------------------------------------- |
| Grafana | **https://grafana.dss.localhost** | user `admin` / password `Password102!` |

Override with `GRAFANA_ADMIN_USER` and `GRAFANA_ADMIN_PASSWORD`. Hostname is controlled by `GRAFANA_HOSTNAME` (default `grafana.dss.localhost`).

### Host ports (fallback / APIs — no Traefik UI)

| What             | Address                 | Notes                                      |
| ---------------- | ----------------------- | ------------------------------------------ |
| Grafana (direct) | `http://localhost:3001` | Use when Traefik is down                   |
| Loki HTTP API    | `http://localhost:3100` | Ready check, push/query API; **no web UI** |
| OTLP gRPC        | `localhost:4317`        | For apps on the host                       |
| OTLP HTTP        | `localhost:4318`        | For apps on the host                       |

Promtail has **no** published UI or Traefik route.

### Docker network (other containers)

Apps on `infra_shared` / `dev_tools` should use the Collector **container name** (not Traefik):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
# or HTTP:
# OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

From the **host** (process not in Docker):

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

______________________________________________________________________

## Host ports

These defaults are unique across this repository (see root `.env.example`).

| Port | Variable                   | Service             |
| ---- | -------------------------- | ------------------- |
| 4317 | `OTEL_COLLECTOR_PORT_GRPC` | Collector OTLP gRPC |
| 4318 | `OTEL_COLLECTOR_PORT_HTTP` | Collector OTLP HTTP |
| 3001 | `GRAFANA_PORT`             | Grafana UI          |
| 3100 | `LOKI_PORT`                | Loki HTTP API       |

Not published to the host (internal only): Collector health `13133`, Promtail `9080`, Loki gRPC `9096`.

______________________________________________________________________

## Configure an application

### Minimal env (OpenTelemetry SDK / auto-instrumentation)

```bash
OTEL_SERVICE_NAME=my-app
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc
# Optional: force only logs if your stack supports signal-specific endpoints
# OTEL_EXPORTER_OTLP_LOGS_ENDPOINT=http://otel-collector:4318
```

- **Logs** sent over OTLP are written to Loki (native OTLP `/otlp`).
- **Traces / metrics** are accepted so exporters do not fail; they are not stored yet.

### Docker Compose snippet for your app

```yaml
services:
  my-app:
    environment:
      OTEL_SERVICE_NAME: my-app
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_EXPORTER_OTLP_PROTOCOL: grpc
    networks:
      - infra_shared   # or dev_tools — same networks as this stack
```

### What Promtail already covers

Any container on the Docker host has **stdout/stderr** scraped by Promtail (Docker service discovery). Labels include:

- `container` — container name
- `compose_service` — Compose service name (when present)
- `compose_project` — Compose project name
- `stream` — `stdout` / `stderr`

You do **not** need OTLP for basic container logs. Use OTLP when you want structured app logs / `service.name` / future trace correlation.

______________________________________________________________________

## Using Grafana

1. Open **https://grafana.dss.localhost** (Traefik + TLS; same `*.dss.localhost` style as Zitadel).
1. Sign in with default account **`admin` / `Password102!`** (or your `GRAFANA_ADMIN_*` values).
1. Go to **Explore** → datasource **Loki** (provisioned from `grafana/provisioning/`).
1. Example LogQL:

```logql
{compose_service="postgres"}
{container=~".+"}
{service_name="my-app"}          # OTLP resource attribute (Loki 3 / OTel)
{compose_service="otel-collector"} |= "error"
```

______________________________________________________________________

## Layout

```
otel/
├── docker-compose.yml          # collector, grafana, loki, promtail
├── otel-config.yaml            # Collector pipelines
├── .env.example                # Ports, versions, resource limits
├── config/
│   ├── loki.yml                # Storage under /loki, retention 168h
│   └── promtail.yml            # Docker SD → Loki push API
├── grafana/provisioning/
│   └── datasources/
│       └── datasources.yml     # Loki as default datasource
├── test-otel.sh                # Smoke test
└── README.md
```

______________________________________________________________________

## Configuration reference

| File / var            | Purpose                                                            |
| --------------------- | ------------------------------------------------------------------ |
| `otel-config.yaml`    | Receivers, processors, exporters, pipelines                        |
| `config/loki.yml`     | Path prefix `/loki`, filesystem store, 7-day retention + compactor |
| `config/promtail.yml` | Docker socket scrape + relabel                                     |
| `GRAFANA_ADMIN_*`     | Grafana login                                                      |
| `*_MEM_LIMIT` / CPU   | Compose `deploy.resources` limits                                  |

After editing Collector or Loki/Promtail config:

```bash
make restart service=otel
# or recreate a single container, e.g.:
docker restart otel-collector
```

______________________________________________________________________

## Operations

```bash
make up service=otel
make down service=otel
make logs service=otel
make restart service=otel

# Collector logs only
docker logs -f otel-collector

# Loki ready (host port; not served via Traefik)
curl -sf http://localhost:3100/ready
```

### Data volumes

Compose project directory is `otel/`, so named volumes are typically:

- `otel_grafana_data`
- `otel_loki_data`

**Migrating from the old `monitoring/` stack:** old volumes (`monitoring_*`) are **not** reused automatically. Start fresh, or copy data between volumes manually if you need history.

### Wipe local log/dashboard data

```bash
make down service=otel
docker volume rm otel_grafana_data otel_loki_data   # names may vary; check: docker volume ls | grep -E 'grafana|loki'
```

______________________________________________________________________

## Troubleshooting

| Symptom                               | What to check                                                                                 |
| ------------------------------------- | --------------------------------------------------------------------------------------------- |
| `https://grafana.dss.localhost` fails | Is Traefik up? Certs for `*.dss.localhost`? Fallback: `http://localhost:3001`.                |
| App cannot reach Collector            | Same Docker network? Hostname `otel-collector`? Host apps use `localhost:4317` (not Traefik). |
| No logs in Grafana                    | Promtail needs Docker socket; Collector needs Loki healthy. Run `./otel/test-otel.sh`.        |
| Grafana has no Loki datasource        | Confirm mount `./grafana/provisioning` and restart Grafana.                                   |
| Loki disk growth                      | Retention is `168h` in `config/loki.yml`; lower `retention_period` if needed.                 |
| Port already allocated                | Change `OTEL_COLLECTOR_PORT_*`, `GRAFANA_PORT`, or `LOKI_PORT` in `otel/.env` / root `.env`.  |

Collector health extension (inside the container network): `http://otel-collector:13133/`.

______________________________________________________________________

## Phase 2 (not included yet)

To store traces / metrics later:

1. Add Tempo (traces) and/or Prometheus (metrics) services.
1. In `otel-config.yaml`, replace `nop` exporters with real backends.
1. Provision extra Grafana datasources (and optional Trace↔Log links).

Until then, keep using this stack as the **default OTLP endpoint** for all projects; only the log path is persisted.
