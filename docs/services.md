# Services & Access Reference

> Detailed catalog of available containerized services, their access points, default credentials, and statistical overview.

______________________________________________________________________

## 📦 Available Services

### Databases

- **Postgres** (PostgreSQL 16) - Default relational database; shared backend for Gitea, Jenkins, Concourse, SonarQube, Zitadel, Inngest, Temporal, Bugsink, Hasura
- **PgVector** (PostgreSQL 17) - Standalone relational database with vector support; shared backend for Hindsight
- **MySQL 8** - Relational database with UTF-8 support
- **MongoDB** - NoSQL document database
- **Adminer** - Universal database administration interface

### Caching & Messaging

- **Redis** - In-memory data structure store with authentication
- **RabbitMQ** - Message broker with management UI
- **Memcached** - Distributed memory caching

### Storage & File Services

- **MinIO** - S3-compatible object storage
- **Mailpit** - Email testing service

### CI/CD & DevOps

- **Gitea** - Git service with version control
- **Jenkins** - Pipeline automation and CI/CD
- **Concourse** - Container-native CI system
- **Act Runner** - GitHub Actions runner for Gitea
- **SonarQube** - Code quality analysis

### Background Jobs & Workflows

- **Inngest** - Event-driven background jobs and workflow engine
- **Node-RED** - Flow-based programming tool for event-driven applications
- **Temporal** - Developer-first open-source orchestrator

### GraphQL APIs

- **Hasura** - Instant GraphQL API on shared Postgres 16 (`hasura` database)

### Agent Memory

- **Hindsight** - MCP agent memory (API + control-plane UI); Traefik-only at `hindsight.dss.localhost` / `hindsight-ui.dss.localhost`; uses shared PgVector

### Web Crawling & Scraping

- **Crawl4AI** - LLM-friendly web crawler and scraping service

### Developer Tools

- **Verdaccio** - Private npm registry at `https://verdaccio.dss.localhost`; host package managers use `http://127.0.0.1:4873/`, and containers on `backend_net` use `http://verdaccio:4873/`. Log in as `admin` with the shared password. Set comma-separated `VERDACCIO_GITHUB_SCOPES`, `VERDACCIO_GITLAB_SCOPES`, and `VERDACCIO_INTERNAL_SCOPES` to route package scopes to those uplinks.
- **LibreOffice Writer** - Headless UNO document runtime (no app code) for document automation: `127.0.0.1:2002` on the host, `libreoffice-writer:2002` on `backend_net`. Ships Vietnamese fonts, UI language, and spell-check. See [libreoffice-writer/README.md](../libreoffice-writer/README.md).

### LLM proxy

- **LiteLLM** - OpenAI-compatible proxy and admin UI at `https://litellm.dss.localhost` (`/ui`, `/v1`). Uses shared Postgres 16 database `litellm`. On an existing Postgres volume, create the database once: `docker exec postgres psql -U postgres -c "CREATE DATABASE litellm;"`

### Observability & Management

- **OTel Collector** - Default OTLP endpoint for apps (`4317` gRPC / `4318` HTTP); logs → Loki
- **Grafana** - Log exploration UI (Loki datasource provisioned)
- **Loki** - Log aggregation and storage
- **Alloy** - Ships Docker container stdout to Loki via the Docker API
- **Traefik** - Reverse proxy and load balancer
- **Zitadel** - Central Identity Provider / OIDC & OAuth2 Server
- **oauth2-proxy** - Opt-in Traefik authentication gateway (`auth.dss.localhost`) for any OIDC issuer
- **Redis Insight** - Redis management UI
- **Dozzle** - Live container log tail (complement to Loki history search)

______________________________________________________________________

## 🌐 Service Access

| Service            | Access Point                                                                                   | Credentials after `make setup`                                                                         |
| :----------------- | :--------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| Postgres 16        | `localhost:5432`                                                                               | `postgres` / `DSS_SHARED_PASSWORD`                                                                     |
| PgVector           | `localhost:5433` (shared backend for Hindsight)                                                | `postgres` / `DSS_SHARED_PASSWORD`                                                                     |
| MySQL 8            | `localhost:3306`                                                                               | `uid` / `DSS_SHARED_PASSWORD`                                                                          |
| MongoDB            | `localhost:27017`                                                                              | `root` / `DSS_SHARED_PASSWORD`                                                                         |
| Redis              | `localhost:6379`                                                                               | - / `DSS_SHARED_PASSWORD`                                                                              |
| RabbitMQ           | `localhost:5672`                                                                               | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| RabbitMQ UI        | `https://rabbitmq.dss.localhost`                                                               | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| Adminer            | `https://adminer.dss.localhost`                                                                | -                                                                                                      |
| ChromaDB Admin     | `https://chromadb-admin.dss.localhost`                                                         | -                                                                                                      |
| Garage Web UI      | `https://garage-ui.dss.localhost`                                                              | UI login: `GARAGE_UI_AUTH_USER_PASS` in `garage_ui/.env`; copy `GARAGE_ADMIN_TOKEN` from `garage/.env` |
| Gitea              | `https://gitea.dss.localhost`                                                                  | -                                                                                                      |
| Crawl4AI           | `https://crawl4ai.dss.localhost`                                                               | Bearer token from `crawl4ai/.env`                                                                      |
| Hindsight API      | `https://hindsight.dss.localhost` (Traefik only; MCP `/mcp/<bank>/`)                           | Set `HINDSIGHT_API_LLM_API_KEY` in `hindsight/.env`                                                    |
| Hindsight UI       | `https://hindsight-ui.dss.localhost` (Traefik only)                                            | -                                                                                                      |
| Hasura             | `https://hasura.dss.localhost`                                                                 | Admin secret: `DSS_SHARED_PASSWORD`                                                                    |
| LiteLLM            | `https://litellm.dss.localhost` (`/ui`, `/v1`)                                                 | UI user `admin` / `LITELLM_MASTER_KEY` from `litellm/.env`                                             |
| Inngest            | `https://inngest.dss.localhost`                                                                | -                                                                                                      |
| Node-RED           | `https://node-red.dss.localhost`                                                               | -                                                                                                      |
| SonarQube          | `https://sonarqube.dss.localhost`                                                              | `admin` / `admin`                                                                                      |
| Jenkins            | `https://jenkins.dss.localhost`                                                                | -                                                                                                      |
| MinIO              | `https://minio.dss.localhost`                                                                  | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| MinIO Console      | `https://minio.dss.localhost`                                                                  | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| Mailpit            | `https://mailpit.dss.localhost`                                                                | -                                                                                                      |
| Concourse          | `https://concourse.dss.localhost`                                                              | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| Redis Insight      | `https://redisinsight.dss.localhost`                                                           | -                                                                                                      |
| Grafana            | `https://grafana.dss.localhost`                                                                | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| Loki               | `http://localhost:3100`                                                                        | -                                                                                                      |
| OTel Collector     | `localhost:4317` (gRPC), `localhost:4318` (HTTP)                                               | Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`                                           |
| LibreOffice Writer | `127.0.0.1:2002` (UNO socket); containers: `libreoffice-writer:2002`                           | -                                                                                                      |
| Temporal UI        | `https://temporal.dss.localhost`                                                               | Opt-in OIDC authentication via `AUTH_*` (off by default)                                               |
| Traefik            | `https://traefik.dss.localhost/dashboard/`                                                     | `admin` / `DSS_SHARED_PASSWORD`                                                                        |
| oauth2-proxy       | `https://auth.dss.localhost` (Traefik only)                                                    | OIDC issuer URL and client id/secret in `oauth2-proxy/.env`                                            |
| Zitadel            | `https://zitadel.dss.localhost`                                                                | `zitadel-admin@zitadel.zitadel.dss.localhost` / `DSS_SHARED_PASSWORD`                                  |
| Verdaccio          | `https://verdaccio.dss.localhost`; npm: `127.0.0.1:4873`; containers: `http://verdaccio:4873/` | `admin` / `DSS_SHARED_PASSWORD`                                                                        |

______________________________________________________________________

## 📊 Service Statistics

- **Total Services**: 20
- **Databases**: 4 (PostgreSQL, MySQL, MongoDB, Redis)
- **Message Brokers**: 1 (RabbitMQ)
- **CI/CD Platforms**: 3 (Jenkins, Concourse, Gitea)
- **Workflow & Background Jobs**: 3 (Inngest, Temporal, Node-RED)
- **Web Crawling & Scraping**: 1 (Crawl4AI)
- **Analysis Tools**: 1 (SonarQube)
- **Storage**: 2 (MinIO, Object Storage)
- **Caching**: 2 (Redis, Memcached)
- **Management UIs**: 3 (Adminer, Redis Insight, Traefik)

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Configuration & Networking Guide](configuration.md)
- [Commands & Operations Guide](usage.md)
- [Troubleshooting & Support](troubleshooting.md)
