---
description: Repository Information Overview
alwaysApply: true
---

# Docker Shared Services Repository Information

## Summary

**Docker Shared Services** is a comprehensive Docker Compose orchestration repository containing 16 pre-configured containerized services for development environments. It provides integrated infrastructure for databases, caching, messaging, storage, CI/CD pipelines, and monitoring tools with automated setup and management workflows.

## Repository Structure

**Root Level Organization:**
- `docker-compose.shared.yml` — Shared network configuration (dev_tools: 10.0.0.0/16)
- `Makefile` — 20+ commands for service orchestration
- `setup-env.sh` — Environment configuration setup and validation utility
- `start-services.sh` — Service management script
- `.env.example` — Global environment template with all service configurations
- Service directories — One per containerized service (traefik, postgres, mysql8, etc.)

**Main Service Components:**
- **Databases**: PostgreSQL (pgvector), MySQL 8, MongoDB, Adminer
- **Caching & Messaging**: Redis, RabbitMQ, Memcached, Redis Insight
- **Storage**: MinIO (S3-compatible), Mailpit (email testing)
- **CI/CD & DevOps**: Gitea, Jenkins, Concourse, Act Runner (Gitea Actions), SonarQube
- **Infrastructure**: Traefik (reverse proxy/load balancer)

## Specification & Tools

**Type**: Docker Compose Configuration Repository  
**Build System**: Docker Compose (orchestrated via Makefile and bash scripts)  
**Required Tools**:
- Docker Engine (20.10+)
- Docker Compose (v2.0+)
- Bash shell
- Make utility

## Key Resources

**Configuration Files Per Service**:
- `[service]/docker-compose.yml` — Service definition with image, ports, volumes, environment, resource limits, health checks
- `[service]/.env.example` — Environment variables template with defaults
- `traefik/config.yml` — Reverse proxy routing configuration
- `traefik/certs/` — SSL/TLS certificates directory

**Global Configuration**:
- `.env` — Root-level environment (created from `.env.example`)
- `.env.example` — Master template containing all service variables, passwords, ports, and resource limits

## Usage & Operations

**Quick Start**:
```bash
chmod +x setup-env.sh
./setup-env.sh all          # Create .env files from templates
make up                     # Start all services
make ps                     # Check status
```

**Key Commands**:

| Command | Purpose |
|---------|---------|
| `make setup` | Create .env files for all services |
| `make up` | Start all services in background |
| `make down` | Stop all services |
| `make restart` | Restart services |
| `make logs` | Stream logs from all services |
| `make health` | Check health status |
| `make clean` | Remove containers and volumes |
| `./start-services.sh up [service]` | Start specific service |
| `./setup-env.sh validate` | Validate environment configuration |

**Docker Compose Direct**:
```bash
docker compose -f docker-compose.shared.yml \
  -f postgres/docker-compose.yml \
  -f redis/docker-compose.yml up -d
```

**Network Access**:
All services communicate via the `dev_tools` bridge network (10.0.0.0/16). Service-to-service connections use container names (e.g., `postgres:5432`, `redis:6379`).

## Service Configuration

**Environment Variables Per Service**:
- **Databases**: User, password, port, database name, CPU/memory limits
- **Caching**: Port, memory limits, authentication credentials
- **CI/CD**: Port mappings, database connections, admin credentials
- **Infrastructure**: Email, log levels, SSL settings, resource allocations

**Default Ports**:
| Service | Port(s) |
|---------|---------|
| PostgreSQL | 5432 |
| MySQL 8 | 3306 |
| MongoDB | 27017 |
| Redis | 6379 |
| RabbitMQ | 5672 (15672 management UI) |
| Memcached | 11211 |
| Gitea | 3000 (SSH: 2222) |
| Jenkins | 8090 |
| SonarQube | 9000 |
| Concourse | 8070 |
| Traefik | 80, 443, 8080 |

## Docker Configuration

**Common Setup Across All Services**:
- Base images: Official Docker Hub images (pgvector, mysql, mongo, redis, rabbitmq, gitea, etc.)
- Restart policy: `always` (via `RESTART_POLICY` env var)
- Resource limits: CPU and memory constraints defined per service
- Health checks: ICMP/HTTP checks for critical services (postgres, gitea)
- Volumes: Named volumes for data persistence
- Networks: All services on shared `dev_tools` bridge network

**Volume Strategy**:
Each service maintains persistent data via named Docker volumes (e.g., `postgres_data`, `gitea_data`, `mongodb_data`).

**Certificate Management**:
Traefik uses SSL/TLS certificates stored in `traefik/certs/`. Setup via mkcert (recommended for dev) or OpenSSL.

## Integration Points

**Database Connectivity**:
- Gitea connects to PostgreSQL for version control data
- SonarQube connects to PostgreSQL for analysis storage
- Jenkins and Concourse use PostgreSQL as backend

**Message Queue**:
Services can connect to RabbitMQ for asynchronous operations via `amqp://guest:guest@rabbitmq:5672`.

**Object Storage**:
MinIO provides S3-compatible storage at `localhost:9002` (or via Traefik routing).

**Reverse Proxy**:
Traefik routes HTTP/HTTPS traffic and load balances across services.

## Setup & Operations

**Environment Setup**:
1. Run `chmod +x setup-env.sh && ./setup-env.sh all` to create `.env` files
2. Customize passwords and ports in individual `.env` files
3. Validate with `./setup-env.sh validate`

**Startup Sequence**:
All services defined in `Makefile` and `start-services.sh` with automatic dependency handling. Run `make up` for orchestrated startup.

**Security Notes**:
- Default passwords (e.g., `password102`) are development-only
- Generate strong passwords (32+ chars) before production: `openssl rand -base64 32`
- SSL certificates must be generated for Traefik HTTPS support

## Validation

**Configuration Validation**:
```bash
make validate                  # Validate all Docker Compose files
./setup-env.sh validate        # Check environment variables
docker compose ps              # Verify running containers
```

**Health Checks**:
- PostgreSQL: `pg_isready`
- Gitea: HTTP health endpoint (`/api/healthz`)
- Most services: Automatic health status available via Docker
- Manual test: `docker compose exec [service] [health_command]`

**Troubleshooting Commands**:
```bash
make logs                      # View all service logs
make logs-service SERVICE=postgres
docker network inspect dev_tools     # Inspect network
docker exec postgres psql -U postgres -c "SELECT version();"
```
