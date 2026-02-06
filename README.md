# Docker Shared Services

![Docker Shared Services](assets/repo.png)

Collection of containerized development services with comprehensive Docker Compose configurations, environment
management, and orchestration tools.

## 🚀 Quick Start

### Setup (5 minutes)

```bash
# 1. Setup environment, network and certificates
make setup

# 2. Start all services (select 'all' or specific service)
make up

# 3. Check status
make ps
```

### Alternative Setup Methods

**Using Docker Compose directly:**

```bash
docker compose -f docker-compose.shared.yml \
  -f postgres/docker-compose.yml \
  -f redis/docker-compose.yml \
  -f monitoring/docker-compose.yml \
  up -d
```

**Manual setup:**

```bash
for dir in */; do
  [ -f "$dir/.env.example" ] && cp "$dir/.env.example" "$dir/.env"
done
make up
```

## 📦 Available Services

### **Databases**

- **PostgreSQL** (pgvector) - Relational database with vector support
- **MySQL 8** - Relational database with UTF-8 support
- **MongoDB** - NoSQL document database
- **Adminer** - Universal database administration interface

### **Caching & Messaging**

- **Redis** - In-memory data structure store with authentication
- **RabbitMQ** - Message broker with management UI
- **Memcached** - Distributed memory caching

### **Storage & File Services**

- **MinIO** - S3-compatible object storage
- **Mailpit** - Email testing service

### **CI/CD & DevOps**

- **Gitea** - Git service with version control
- **Jenkins** - Pipeline automation and CI/CD
- **Concourse** - Container-native CI system
- **Act Runner** - GitHub Actions runner for Gitea
- **SonarQube** - Code quality analysis

### **Monitoring & Management**

- **Grafana** - Analytics and monitoring dashboard
- **Loki** - Log aggregation system
- **Promtail** - Log shipper for Docker containers
- **Traefik** - Reverse proxy and load balancer
- **Redis Insight** - Redis management UI

## 📋 Features

- ✅ Comprehensive `.env.example` for each service
- ✅ Health checks for critical services
- ✅ CPU/Memory resource limits and reservations
- ✅ Persistent volumes for data
- ✅ Service dependencies management
- ✅ Shared `dev_tools` network (10.0.0.0/16)
- ✅ Makefile with 20+ commands
- ✅ Automated setup scripts with validation

## 🔧 Usage & Commands

### **Makefile (Recommended)**

```bash
make help           # Show all commands
make setup          # Setup environment files, network and certs
make cert           # Generate SSL certificates
make up             # Start services (interactive or specific)
make down           # Stop and remove services
make stop           # Stop services (keep containers)
make ps             # Show service status
make logs           # View logs
make clean          # Remove containers & volumes
make restart        # Restart services
```

### **Docker Compose Direct**

```bash
docker compose ps                    # View status
docker compose logs -f               # View logs
docker compose logs -f [service]     # Specific service
docker compose down                  # Stop all
docker compose down -v               # Stop and remove volumes
```

## 🌐 Service Access

| Service       | Access Point           | Default Credentials  |
|---------------|------------------------|----------------------|
| PostgreSQL    | localhost:5432         | postgres/password102 |
| MySQL 8       | localhost:3306         | uid/password102      |
| MongoDB       | localhost:27017        | root/password102     |
| Redis         | localhost:6379         | - / password102      |
| RabbitMQ      | localhost:5672         | guest/guest          |
| RabbitMQ UI   | http://localhost:15672 | guest/guest          |
| Adminer       | http://localhost:8081  | -                    |
| Gitea         | http://localhost:3000  | -                    |
| SonarQube     | http://localhost:9000  | admin/admin          |
| Jenkins       | http://localhost:8090  | -                    |
| MinIO         | http://localhost:9002  | admin/password102    |
| MinIO Console | http://localhost:9003  | admin/password102    |
| Mailpit       | http://localhost:8025  | -                    |
| Concourse     | http://localhost:8070  | admin/password102    |
| Redis Insight | http://localhost:5540  | -                    |
| Grafana       | http://localhost:3001  | admin/password102    |
| Loki          | http://localhost:3100  | -                    |
| Traefik       | http://localhost:8080  | -                    |

## ⚙️ Configuration

### **Environment Files**

Each service has a `.env.example` file. Copy and customize:

```bash
cp postgres/.env.example postgres/.env
# Edit postgres/.env with your values
```

### **Change Passwords**

```bash
# Edit service .env file
POSTGRES_PASSWORD=your_strong_password
MYSQL_ROOT_PASSWORD=your_strong_password
MONGO_ROOT_PASSWORD=your_strong_password
```

### **Change Ports**

```bash
# Edit service .env file
POSTGRES_PORT=5433          # Instead of 5432
MYSQL_PORT=3307            # Instead of 3306
```

### **Resource Limits**

```env
POSTGRES_CPUS_LIMIT=2
POSTGRES_MEMORY_LIMIT=2G
POSTGRES_CPUS_RESERVED=1
POSTGRES_MEMORY_RESERVED=1G
```

### **Enable/Disable Services**

Edit `start-services.sh` or `Makefile` and comment out unwanted services.

### **Network Configuration**

All services use the `dev_tools` bridge network:

- **Network**: dev_tools
- **Subnet**: 10.0.0.0/16
- **Gateway**: 10.0.0.1

Services communicate using container names:

```bash
# PostgreSQL
postgres://postgres:password102@postgres:5432/mydb

# Redis
redis://:password102@redis:6379

# RabbitMQ
amqp://guest:guest@rabbitmq:5672

# Service-to-service
POSTGRES_HOST=postgres
REDIS_HOST=redis
RABBITMQ_HOST=rabbitmq
```

### **Network Inspection**

```bash
docker network ls                            # List networks
docker network inspect dev_tools             # Inspect network
docker network inspect dev_tools | grep -A 20 "Containers"  # Check containers
docker exec [container] ping [other_container]  # Test connectivity
```

### **SSL/TLS Certificate Setup (Traefik)**

Traefik requires SSL/TLS certificates for HTTPS support. The easiest way is using `mkcert`.

#### **Option 1: Using Makefile (Recommended)**

```bash
# 1. Install mkcert
# macOS: brew install mkcert
# Linux: Follow mkcert installation guide

# 2. Run the make command
make cert
```

#### **Option 2: Manual with mkcert**

```bash
mkdir -p traefik/certs

openssl req -x509 -newkey rsa:4096 -keyout traefik/certs/server.key \
  -out traefik/certs/server.crt -days 365 -nodes \
  -subj "/CN=localhost"
```

#### **Important Notes**

- **Certificate files are in `.gitignore`** - They are NOT committed to repository
- **Generate fresh certificates** for each environment (development, staging, production)
- Certificates are located in: `traefik/certs/server.crt` and `traefik/certs/server.key`
- Update certificate validity period in mkcert command as needed (default: 2 years)

#### **Verify Certificates**

```bash
# Check certificate details
openssl x509 -in traefik/certs/server.crt -text -noout

# Check expiration
openssl x509 -in traefik/certs/server.crt -noout -dates
```

## 🔐 Security Notes

⚠️ **Default passwords are for development only!**

### **Before Production**

1. Change all default passwords (minimum 32 characters)
2. Use strong, unique passwords for each service
3. Secure sensitive data with proper secrets management
4. Review and customize resource limits
5. Set appropriate firewall rules

### **Generate Strong Passwords**

```bash
openssl rand -base64 32
```

## 🐛 Troubleshooting

### **Services won't start**

```bash
make logs              # Check logs
make validate          # Validate configuration
make restart           # Restart services
make logs-service SERVICE=postgres  # Specific service
```

### **Port already in use**

```bash
lsof -i :5432          # Find process using port
# Update .env to use different port
make restart
```

### **Out of memory**

```bash
# Reduce resource limits in .env
POSTGRES_MEMORY_LIMIT=512M
POSTGRES_MEMORY_RESERVED=256M
make restart
```

### **Network issues**

```bash
docker network inspect dev_tools
docker logs [container_id]
docker exec [container1] ping [container2]
```

### **Volume permission issues**

```bash
docker volume ls | grep dev_      # List volumes
docker volume rm [volume_name]    # Remove volume (data will be lost)
docker volume prune               # Remove unused volumes
```

### **Common Issues**

| Problem                   | Solution                                                             |
|---------------------------|----------------------------------------------------------------------|
| Services stuck "starting" | Wait 30-60 seconds, check logs, restart: `make restart`              |
| Can't connect to database | Verify port mapping, check .env passwords, test: `docker-compose ps` |
| Out of disk space         | Run `make prune`, remove images: `docker image prune -a`             |
| Need to reset everything  | Run `make clean` then `make up`                                      |

### **Getting Help**

```bash
make health              # Check service health
docker-compose ps        # View status
make logs                # View logs

# Test connectivity
docker compose exec postgres psql -U postgres -c "SELECT version();"
docker compose exec redis redis-cli ping
docker compose exec mysql8 mysqladmin ping -u root -p
```

## 🗑️ Cleanup

### **Stop services (keep data)**

```bash
make down
```

### **Stop and remove volumes (delete data)**

```bash
make clean
```

### **Deep cleanup**

```bash
make clean
make prune
docker system prune -a --volumes
```

## 📋 Project Structure

```
docker-shared-services/
├── docker-compose.shared.yml      # Shared network definition
├── .env.example                   # Root environment template
├── Makefile                       # All-in-one management commands
├── bin/                           # Python management logic
├── README.md                      # This file
│
├── postgres/
│   ├── docker-compose.yml
│   └── .env.example
│
├── mysql8/
│   ├── docker-compose.yml
│   └── .env.example
│
├── mongodb/
│   ├── docker-compose.yml
│   └── .env.example
│
├── redis/
│   ├── docker-compose.yml
│   ├── .env.example
│   └── redis.conf
│
├── [... other services ...]
```

## 📊 Service Statistics

- **Total Services**: 16
- **Databases**: 4 (PostgreSQL, MySQL, MongoDB, Redis)
- **Message Brokers**: 1 (RabbitMQ)
- **CI/CD Platforms**: 3 (Jenkins, Concourse, Gitea)
- **Analysis Tools**: 1 (SonarQube)
- **Storage**: 2 (MinIO, Object Storage)
- **Caching**: 2 (Redis, Memcached)
- **Management UIs**: 3 (Adminer, Redis Insight, Traefik)

## 🎯 Pro Tips

1. **Use Makefile** - Easier than docker-compose commands
2. **Keep backups** of important databases before major changes
3. **Monitor resources** - Watch with `docker stats`
4. **Use .env files** - Don't hardcode sensitive values
5. **Check logs first** - Most issues are revealed in logs
6. **Use container names** for inter-service communication
7. **Always use healthchecks** for critical services

## 🤝 Contributing

Feel free to improve this setup by:

- Adding new services
- Improving documentation
- Fixing issues
- Optimizing configurations

## 📝 License

See LICENSE file for details.

## 🔗 Related Resources

- **[Docker Documentation](https://docs.docker.com/)**
- **[Docker Compose Documentation](https://docs.docker.com/compose/)**
- **[Makefile](Makefile)** - All available commands
- **Individual `.env.example`** files - Service-specific variables

## 📞 Support

For issues or questions:

1. Check this README for common solutions
2. Review service-specific `.env.example` files
3. Check Docker logs: `make logs`
4. Validate configuration: `make validate`
5. Inspect network: `docker network inspect dev_tools`

---

**Last Updated**: February 2026
**Docker Version Required**: 20.10+
**Docker Compose Version Required**: 2.0+
