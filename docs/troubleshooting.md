# Troubleshooting & Support

> Solutions for common issues, debugging guides, support channels, and security instructions.

______________________________________________________________________

## 🔐 Security Notes

> [!WARNING]
> Default passwords configured in this repository are for development only!

### Before Production

1. Change all default passwords (minimum 32 characters).
1. Use strong, unique passwords for each service.
1. Secure sensitive data with proper secrets management.
1. Review and customize resource limits.
1. Set appropriate firewall rules.

### Generate Strong Passwords

```bash
openssl rand -base64 32
```

______________________________________________________________________

## 🐛 Troubleshooting

### Services won't start

```bash
make logs              # Check logs
make validate          # Validate configuration
make restart           # Restart services
make logs service=pgvector  # Logs for a specific service
make health            # Check health status of all (or one) services
```

### Port already in use

```bash
lsof -i :5432          # Find process using port
# Update .env to use different port
make restart
```

> [!NOTE]
> Postgres 16 (`POSTGRES16_PORT`, default `5432`) is the default shared DB
> backend other services connect to. PgVector (`POSTGRES_PORT`, default
> `5433`) is a separate, standalone Postgres 17 + vector-extension instance
> that no other service in this repo depends on — the two are intentionally
> kept on different host ports so they can run at the same time.

### Out of memory

```bash
# Reduce resource limits in .env
POSTGRES_MEMORY_LIMIT=512M
POSTGRES_MEMORY_RESERVED=256M
make restart
```

### Network issues

```bash
docker network inspect infra_shared
docker logs [container_id]
docker exec [container1] ping [container2]
```

### Volume permission issues

```bash
docker volume ls | grep dev_      # List volumes
docker volume rm [volume_name]    # Remove volume (data will be lost)
docker volume prune               # Remove unused volumes
```

### Common Issues

| Problem                   | Solution                                                             |
| :------------------------ | :------------------------------------------------------------------- |
| Services stuck "starting" | Wait 30-60 seconds, check logs, restart: `make restart`              |
| Can't connect to database | Verify port mapping, check .env passwords, test: `docker-compose ps` |
| Out of disk space         | Run `make prune`, remove images: `docker image prune -a`             |
| Need to reset everything  | Run `make remove-all` then `make up`                                 |

### Getting Help

```bash
make health              # Check service health
docker-compose ps        # View status
make logs                # View logs

# Test connectivity
docker compose exec pgvector psql -U postgres -c "SELECT version();"
docker compose exec redis redis-cli ping
docker compose exec mysql8 mysqladmin ping -u root -p
```

______________________________________________________________________

## 📞 Support

For issues or questions:

1. Check this troubleshooting guide for common solutions.
1. Review service-specific `.env.example` files.
1. Check Docker logs: `make logs`
1. Validate configuration: `make validate`
1. Inspect networks: `docker network inspect infra_shared` and `docker network inspect dev_tools`

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Configuration & Networking Guide](configuration.md)
- [Commands & Operations Guide](usage.md)
