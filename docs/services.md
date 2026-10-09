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

### Observability & Management

- **OTel Collector** - Default OTLP endpoint for apps (`4317` gRPC / `4318` HTTP); logs → Loki
- **Grafana** - Log exploration UI (Loki datasource provisioned)
- **Loki** - Log aggregation and storage
- **Promtail** - Ships Docker container stdout to Loki
- **Traefik** - Reverse proxy and load balancer
- **Zitadel** - Central Identity Provider / OIDC & OAuth2 Server
- **oauth2-proxy** - Opt-in Traefik authentication gateway (`auth.dss.localhost`) backed by Zitadel
- **Redis Insight** - Redis management UI
- **Dozzle** - Live container log tail (complement to Loki history search)

______________________________________________________________________

## 🌐 Service Access

| Service        | Access Point                                                         | Default Credentials                                            |
| :------------- | :------------------------------------------------------------------- | :------------------------------------------------------------- |
| Postgres 16    | `localhost:5432`                                                     | `postgres` / `Password102!`                                    |
| PgVector       | `localhost:5433` (shared backend for Hindsight)                      | `postgres` / `Password102!`                                    |
| MySQL 8        | `localhost:3306`                                                     | `uid` / `Password102!`                                         |
| MongoDB        | `localhost:27017`                                                    | `root` / `Password102!`                                        |
| Redis          | `localhost:6379`                                                     | - / `Password102!`                                             |
| RabbitMQ       | `localhost:5672`                                                     | `guest` / `guest`                                              |
| RabbitMQ UI    | `https://rabbitmq.dss.localhost`                                    | `guest` / `guest`                                              |
| Adminer        | `https://adminer.dss.localhost`                                    | -                                                              |
| ChromaDB Admin | `https://chromadb-admin.dss.localhost`                             | -                                                              |
| Gitea          | `https://gitea.dss.localhost`                                      | -                                                              |
| Crawl4AI       | `https://crawl4ai.dss.localhost`                                   | Bearer token from `crawl4ai/.env`                              |
| Hindsight API  | `https://hindsight.dss.localhost` (Traefik only; MCP `/mcp/<bank>/`) | Set `HINDSIGHT_API_LLM_API_KEY` in `hindsight/.env`            |
| Hindsight UI   | `https://hindsight-ui.dss.localhost` (Traefik only)                  | -                                                              |
| Hasura         | `https://hasura.dss.localhost`                                      | Admin secret: `Password102!`                                   |
| Inngest        | `https://inngest.dss.localhost`                                    | -                                                              |
| Node-RED       | `https://node-red.dss.localhost`                                   | -                                                              |
| SonarQube      | `https://sonarqube.dss.localhost`                                  | `admin` / `admin`                                              |
| Jenkins        | `https://jenkins.dss.localhost`                                    | -                                                              |
| MinIO          | `https://minio.dss.localhost`                                      | `admin` / `Password102!`                                       |
| MinIO Console  | `https://minio.dss.localhost`                                      | `admin` / `Password102!`                                       |
| Mailpit        | `https://mailpit.dss.localhost`                                    | -                                                              |
| Concourse      | `https://concourse.dss.localhost`                                  | `admin` / `Password102!`                                       |
| Redis Insight  | `https://redisinsight.dss.localhost`                               | -                                                              |
| Grafana        | `https://grafana.dss.localhost`                                    | `admin` / `Password102!`                                       |
| Loki           | `http://localhost:3100`                                              | -                                                              |
| OTel Collector | `localhost:4317` (gRPC), `localhost:4318` (HTTP)                     | Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317`   |
| Temporal UI    | `https://temporal.dss.localhost`                                    | Opt-in Zitadel via `AUTH_*` (off by default)                   |
| Traefik        | `http://localhost:8080`                                              | -                                                              |
| oauth2-proxy   | `https://auth.dss.localhost` (Traefik only)                          | Zitadel OIDC client id/secret in `oauth2-proxy/.env`           |
| Zitadel        | `https://zitadel.dss.localhost`                                     | `zitadel-admin@zitadel.zitadel.dss.localhost` / `Password102!` |

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
