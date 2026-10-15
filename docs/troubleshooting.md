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

### Rotate the shared password

`make setup` generates a `DSS_SHARED_PASSWORD` of at least 15 characters with lowercase, uppercase, digit, and special characters. A new password passed via `password=…` or the `DSS_SHARED_PASSWORD` environment variable must meet the same rules.

Older installs may hold a letters-and-digits password. Setup keeps it and prints a warning, because MySQL, Redis, and other data services store the password in their volumes on first start. Zitadel is the exception: `make up service=zitadel` refuses a weak `ZITADEL_ADMIN_PASSWORD`, because Zitadel's default policy requires a symbol.

Postgres 16 reapplies `POSTGRES_PASSWORD` each time its container starts, including when the data directory already exists. Clients such as Zitadel authenticate over the network with scram. `pg_isready` does not check that password, so the healthcheck connects to the container's own IP.

To rotate:

1. For MySQL, Redis, and the other data services, change the password inside each running service first, or wipe its volume if the data is disposable. Postgres picks up `POSTGRES16_PASSWORD` on the next container start.
1. Write the new value to every `.env`:
   ```bash
   make passwords password='New-Strong.Password1' force=1
   ```
1. Recreate the affected services: `make restart service=<name>` (or `make down` then `make up`).

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
> backend other services connect to. PgVector (`PGVECTOR_PORT`, default
> `5433`) is a separate, standalone Postgres 17 + vector-extension instance
> used by Hindsight. The two are intentionally kept on different host ports
> so they can run at the same time.

### Out of memory

```bash
# Reduce resource limits in .env
PGVECTOR_MEMORY_LIMIT=512M
PGVECTOR_MEMORY_RESERVED=256M
make restart
```

### Network issues

```bash
docker network inspect traefik_proxy
docker network inspect backend_net
docker network inspect data_net
docker logs [container_id]
docker exec [container1] ping [container2]
```

### Volume permission issues

```bash
docker volume ls | grep dev_      # List volumes
docker volume rm [volume_name]    # Remove volume (data will be lost)
docker volume prune               # Remove unused volumes
```

### oauth2-proxy / Zitadel UI login

| Problem                                                    | Solution                                                                                                                                                   |
| :--------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Redirect loop or callback error                            | Confirm Zitadel app redirect URI is exactly `https://auth.dss.localhost/oauth2/callback` and `OAUTH2_PROXY_CLIENT_*` match the app                         |
| Browser displays a “Found” link instead of opening Zitadel | Ensure shared ForwardAuth points to oauth2-proxy `/`, which returns the login redirect as an actual 302; recreate `oauth2-proxy` after changing its labels |
| `oauth2-proxy` cannot discover issuer                      | Ensure Traefik + Zitadel are up; container uses `extra_hosts: zitadel.dss.localhost:host-gateway` to reach host Traefik                                    |
| UI still public after enabling auth                        | Set both `AUTH_ENABLED=true` and `AUTH_MIDDLEWARE=auth-default`, then `make restart service=<folder>`                                                      |
| API clients fail on chromadb/qdrant Traefik hosts          | Auth is opt-in; use `AUTH_MIDDLEWARE=auth-none` for API-first access through the domain and provide native keys such as `QDRANT_API_KEY`                   |
| Cookie not shared across UIs                               | Cookie domain must be `.dss.localhost` (default); browse via HTTPS Traefik hosts, not raw localhost ports                                                  |
| Do not put gateway in front of Zitadel                     | Keep Zitadel routers without `AUTH_MIDDLEWARE`                                                                                                             |

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
1. Inspect networks: `docker network inspect traefik_proxy`, `docker network inspect backend_net`, and `docker network inspect data_net`

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Configuration & Networking Guide](configuration.md)
- [Commands & Operations Guide](usage.md)
