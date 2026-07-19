# Services & Access Reference

> Detailed catalog of available containerized services, their access points, default credentials, and statistical overview.

---

## 📦 Available Services

### Databases

- **PgVector** (PostgreSQL 17) - Relational database with vector support
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

### Web Crawling & Scraping

- **Crawl4AI** - LLM-friendly web crawler and scraping service

### Monitoring & Management

- **Grafana** - Analytics and monitoring dashboard
- **Loki** - Log aggregation system
- **Promtail** - Log shipper for Docker containers
- **Traefik** - Reverse proxy and load balancer
- **Redis Insight** - Redis management UI

---

## 🌐 Service Access

| Service | Access Point | Default Credentials |
| :--- | :--- | :--- |
| PgVector | `localhost:5432` | `postgres` / `password102` |
| MySQL 8 | `localhost:3306` | `uid` / `password102` |
| MongoDB | `localhost:27017` | `root` / `password102` |
| Redis | `localhost:6379` | - / `password102` |
| RabbitMQ | `localhost:5672` | `guest` / `guest` |
| RabbitMQ UI | `http://localhost:15672` | `guest` / `guest` |
| Adminer | `http://localhost:8081` | - |
| Gitea | `http://localhost:3000` | - |
| Crawl4AI | `http://localhost:11235` (Host: `crawl4ai.localhost`) | - |
| Inngest | `http://localhost:8288` (Host: `inngest.localhost`) | - |
| Node-RED | `http://localhost:1880` (Host: `node-red.localhost`) | - |
| SonarQube | `http://localhost:9000` | `admin` / `admin` |
| Jenkins | `http://localhost:8090` | - |
| MinIO | `http://localhost:9002` | `admin` / `password102` |
| MinIO Console | `http://localhost:9003` | `admin` / `password102` |
| Mailpit | `http://localhost:8025` | - |
| Concourse | `http://localhost:8070` | `admin` / `password102` |
| Redis Insight | `http://localhost:5540` | - |
| Grafana | `http://localhost:3001` | `admin` / `password102` |
| Loki | `http://localhost:3100` | - |
| Temporal UI | `http://localhost:8083` (Host: `temporal.localhost`) | - |
| Traefik | `http://localhost:8080` | - |

---

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

---

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Configuration & Networking Guide](configuration.md)
- [Commands & Operations Guide](usage.md)
- [Troubleshooting & Support](troubleshooting.md)
