---
description: Repository Information Overview
alwaysApply: true
---

# Docker Shared Services Information

## Summary
**Docker Shared Services** is a comprehensive Docker Compose orchestration repository containing 16+ pre-configured containerized services for development environments. It provides integrated infrastructure for databases, caching, messaging, storage, CI/CD pipelines, and monitoring tools, all managed through a centralized **Makefile** and Python-based management logic.

## Structure
- **Root Level**: Contains global configurations (`.env.example`, `docker-compose.shared.yml`), the orchestrating `Makefile`, and management logic in `bin/`.
- **Service Directories**: Each service (e.g., `pgvector/`, `redis/`, `gitea/`) contains its own `docker-compose.yml` and `.env.example`.
- **Infrastructure**: `traefik/` acts as the reverse proxy and load balancer for all services.
- **Monitoring**: `monitoring/` contains configurations for Grafana, Loki, and Promtail.

## Specification & Tools
**Type**: Docker Compose Configuration Repository  
**Build System**: Docker Compose (orchestrated via **Makefile**)  
**Required Tools**:
- **Docker Engine**: 20.10+
- **Docker Compose**: v2.0+
- **Make**: For command orchestration
- **Python 3**: Used by internal management scripts in `bin/`
- **mkcert**: (Optional) For local SSL/TLS certificate generation

## Key Resources
**Main Components**:
- **Databases**: PgVector (PostgreSQL 17), MySQL 8, MariaDB, MongoDB, ChromaDB, Qdrant, Supabase (minimal Auth/DB/Storage/Studio)
- **Caching & Messaging**: Redis, RabbitMQ, Memcached
- **DevOps & CI/CD**: Gitea, Jenkins, Concourse, SonarQube, Act Runner
- **Management UIs**: Adminer, Dockge, Portainer, Redis Insight, Dozzle
- **Automation & Tools**: n8n, Appsmith, MinIO, Mailpit, PocketBase

**Configuration Structure**:
- **Global `.env`**: Created from root `.env.example`, contains shared variables and resource limits.
- **Service `.env`**: Each directory has its own `.env` (copy from `.env.example`) for service-specific overrides.
- **Shared networks**: External bridge networks `infra_shared` (10.0.0.0/16) and `dev_tools` (10.1.0.0/16), declared in `docker-compose.shared.yml`. Docker cannot assign the same CIDR to two networks; adjacent `/16` blocks keep addressing under `10.0.0.0/8`. Most services attach to both so Traefik (on `infra_shared`) and legacy compose stacks (on `dev_tools`) can reach them by container name on the appropriate network.

## Usage & Operations
**Key Commands**:
```bash
make setup          # Initialize environment files, shared networks, and certificates
make up             # Start services (interactive or specific)
make ps             # Show status of all services
make logs           # View aggregated logs
make down           # Stop and remove services
make stop           # Stop services but keep containers
make remove-all     # Remove containers and volumes (WIPE DATA)
make health         # Check service health status
make cert           # Generate SSL certificates using mkcert
```

**Service Access**:
Services are accessible via `localhost` on specific ports or through Traefik routing (e.g., `http://appsmith.localhost`). Default credentials (e.g., `admin/password102`) are provided in `README.md` for development.

## Docker Configuration
**Common Patterns**:
- **Base Images**: Official Docker Hub images.
- **Resource Limits**: CPU and Memory limits/reservations defined via environment variables.
- **Persistence**: Named Docker volumes (e.g., `pgvector_data`, `gitea_data`) for data durability.
- **Networking**: `docker-compose.shared.yml` defines external networks `infra_shared` and `dev_tools`. Traefik is configured to use `infra_shared` for Docker provider routing.

## Validation
**Quality Checks**:
- `make validate`: Validates all Docker Compose files for syntax and configuration errors.
- **Health Checks**: Integrated Docker healthchecks for critical services (PgVector, Gitea, etc.).

**Integration Points**:
- **Database Backend**: Gitea, SonarQube, Jenkins, and Concourse are configured to connect to the shared PgVector service.
- **Log Aggregation**: Promtail ships logs from all containers to Loki, visualized in Grafana.
- **Reverse Proxy**: Traefik handles SSL termination and routing based on container labels.
