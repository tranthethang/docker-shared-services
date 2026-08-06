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

### Change Passwords

```bash
# Edit service .env file
POSTGRES_PASSWORD=your_strong_password
MYSQL_ROOT_PASSWORD=your_strong_password
MONGO_ROOT_PASSWORD=your_strong_password
```

### Change Ports

```bash
# Edit service .env file
POSTGRES_PORT=5433          # Instead of 5432
MYSQL_PORT=3307            # Instead of 3306
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
# PgVector
postgres://postgres:password102@pgvector:5432/mydb

# Redis
redis://:password102@redis:6379

# RabbitMQ
amqp://guest:guest@rabbitmq:5672

# Service-to-service
POSTGRES_HOST=pgvector
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

## 🔒 SSL/TLS Certificate Setup (Traefik)

Traefik requires SSL/TLS certificates for HTTPS support. The easiest way is using `mkcert`.

### Option 1: Using Makefile (Recommended)

```bash
# 1. Install mkcert
# macOS: brew install mkcert
# Linux: Follow mkcert installation guide

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
