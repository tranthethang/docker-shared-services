# Docker Shared Services

![Docker Shared Services](assets/repo.png)

Collection of containerized development services with comprehensive Docker Compose configurations, environment management, and orchestration tools.

> [!IMPORTANT]
> **OS Compatibility:** This repository is designed and optimized exclusively for **macOS** and **Linux**. It relies on Unix-specific tooling and scripts; **Windows is not supported**.

## 🚀 Quick Start

### Setup (5 minutes)

```bash
# 1. Setup environment, shared networks, and certificates
make setup

# 2. Start services (interactive prompt allows selecting 'all' or specific service)
make up

# 3. Check status
make ps
```

### Alternative Setup Methods

**Using Docker Compose directly:**

```bash
docker compose -f docker-compose.shared.yml \
  -f pgvector/docker-compose.yml \
  -f redis/docker-compose.yml \
  -f monitoring/docker-compose.yml \
  up -d
```

______________________________________________________________________

## 📚 Detailed Documentation

To explore service options, networking details, commands, and troubleshooting, refer to the following guides:

- **[Services & Access Reference](docs/services.md)**: Catalog of available services, open ports, default credentials, and statistics.
- **[Configuration & Networking Guide](docs/configuration.md)**: Customizing environment variables, ports, passwords, resource constraints, Docker networking, and SSL/TLS certificates.
- **[Commands & Operations Guide](docs/usage.md)**: Complete Makefile orchestrations, Docker Compose command examples, cleanup procedures, and development pro-tips.
- **[Troubleshooting & Support](docs/troubleshooting.md)**: Common startup issues, port conflicts, out-of-memory errors, and diagnostic steps.

______________________________________________________________________

## 📋 Project Structure

```
docker-shared-services/
├── docker-compose.shared.yml      # Shared external networks (infra_shared, dev_tools)
├── docs/                          # Detailed documentation guides
│   ├── services.md
│   ├── configuration.md
│   ├── usage.md
│   └── troubleshooting.md
├── Makefile                       # All-in-one management commands
├── bin/                           # Python management logic
├── [service directories]/         # (e.g., pgvector/, redis/, mongodb/, etc.)
```

______________________________________________________________________

## 🤝 Contributing & Support

- Refer to the [Troubleshooting & Support](docs/troubleshooting.md) guide for issues.
- Contributions are welcome! Feel free to open issues or submit pull requests.
- License: See [LICENSE](LICENSE) file.

______________________________________________________________________

**Docker Version Required**: 20.10+ | **Docker Compose Version Required**: 2.0+
