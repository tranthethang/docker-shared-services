# Docker Shared Services

A collection of Docker Compose configurations for common development tools and services, designed to run together on a shared Docker network for local development environments.

## Overview

This repository provides pre-configured Docker Compose setups for various development tools including databases, message queues, CI/CD systems, and monitoring tools. All services are connected to a shared `dev_tools` network and can be accessed via Traefik reverse proxy using localhost subdomains.

## Services Included

### Databases
- **PostgreSQL** (`pgvector/pgvector:pg17`) - PostgreSQL with pgvector extension for AI/vector operations
- **MySQL 8** - MySQL 8 database server
- **MongoDB** - NoSQL document database
- **Redis** - In-memory data structure store with persistence

### Development Tools
- **Adminer** - Database administration tool (supports MySQL, PostgreSQL, SQLite, etc.)
- **RedisInsight** - Redis GUI for development and debugging
- **SonarQube** - Code quality and security analysis platform
- **Gitea** - Lightweight self-hosted Git service
- **Jenkins** - Automation server for CI/CD
- **Concourse** - CI/CD system designed for pipelines
- **Act Runner** - GitHub Actions runner for local testing

### Infrastructure
- **RabbitMQ** - Message broker for AMQP protocol
- **Memcached** - Distributed memory object caching system
- **MinIO** - S3-compatible object storage server
- **Mailpit** - Email testing tool for developers
- **Traefik** - Modern HTTP reverse proxy and load balancer

## Prerequisites

- Docker and Docker Compose installed
- At least 4GB RAM available (recommended 8GB+ for all services)
- Ports 80, 443, and various service ports available

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/docker-shared-services.git
   cd docker-shared-services
   ```

2. **Create the shared Docker network:**
   ```bash
   docker network ls | grep -q dev_tools || docker network create dev_tools
   ```

3. **Configure environment variables:**
   Copy `.env.example` files from each service directory to `.env` and modify as needed:
   ```bash
   # Example for PostgreSQL
   cp postgres/.env.example postgres/.env
   # Edit postgres/.env with your preferred settings
   ```

4. **Start services:**
   Navigate to each service directory and run:
   ```bash
   cd postgres
   docker-compose up -d
   ```

   Or start all services at once (requires custom orchestration script).

## Service URLs

Once Traefik is running, services are accessible at:

- Adminer: http://adminer.localhost
- Mailpit: http://mailpit.localhost
- RabbitMQ Management: http://rabbitmq.localhost
- RedisInsight: http://redisinsight.localhost
- Gitea: http://gitea.localhost
- Jenkins: http://jenkins.localhost
- Concourse: http://concourse.localhost
- SonarQube: http://sonarqube.localhost
- MinIO: http://minio.localhost

## Configuration

Each service directory contains:
- `docker-compose.yml` - Service configuration
- `.env.example` - Environment variable template

### Common Environment Variables

- `RESTART_POLICY` - Container restart policy (default: always)
- Service-specific ports and credentials

### Resource Limits

Some services (like PostgreSQL) include CPU and memory limits that can be configured via environment variables.

## Data Persistence

All services use named Docker volumes for data persistence. Volume names follow the pattern `{service}_data`.

## Networking

All services connect to the `dev_tools` bridge network, allowing inter-service communication using container names as hostnames.

## Development Workflow

1. Start Traefik first for routing
2. Start databases (PostgreSQL, MySQL, MongoDB, Redis)
3. Start supporting services (RabbitMQ, MinIO, Memcached)
4. Start development tools (Jenkins, SonarQube, Gitea)
5. Start testing tools (Mailpit, Adminer, RedisInsight)

## Troubleshooting

- **Port conflicts**: Check if required ports are available
- **Memory issues**: Increase Docker memory allocation
- **Network issues**: Ensure `dev_tools` network exists
- **Permission issues**: Check Docker daemon permissions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add new service configurations
4. Test thoroughly
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Author

Thế Thắng Trần