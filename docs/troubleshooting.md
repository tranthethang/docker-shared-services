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

Older installs may hold a letters-and-digits password. Setup keeps it and prints a warning, because MySQL, Redis, and other data services store the password in their volumes on first start. Zitadel is the exception: `dss up --service zitadel` refuses a weak `ZITADEL_ADMIN_PASSWORD`, because Zitadel's default policy requires a symbol.

Postgres 16 reapplies `POSTGRES_PASSWORD` each time its container starts, including when the data directory already exists. Clients such as Zitadel authenticate over the network with scram. `pg_isready` does not check that password, so the healthcheck connects to the container's own IP.

To rotate:

1. For MySQL, Redis, and the other data services, change the password inside each running service first, or wipe its volume if the data is disposable. Postgres picks up `POSTGRES16_PASSWORD` on the next container start.
1. Write the new value to every `.env`:
   ```bash
   cli/target/release/dss env passwords --password 'New-Strong.Password1' --force
   ```
1. Recreate the affected services: `cli/target/release/dss restart --service <name>` (or `down` then `up`).

______________________________________________________________________

## 🐛 Troubleshooting

### Services won't start

```bash
cli/target/release/dss logs --service <name>  # Check logs
make validate                                 # Validate configuration
cli/target/release/dss restart --service <name> # Restart a service
cli/target/release/dss logs --service pgvector  # Logs for a specific service
cli/target/release/dss health                 # Check health status of all (or one) services
```

### Port already in use

```bash
lsof -i :5432          # Find process using port
# Update .env to use different port
cli/target/release/dss restart --service postgres
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
cli/target/release/dss restart --service pgvector
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

### oauth2-proxy / OIDC UI login

| Problem                                                    | Solution                                                                                                                                                                           |
| :--------------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Redirect loop or callback error                            | Confirm the OIDC client redirect URI is exactly `https://auth.sandbox.localhost/oauth2/callback` and `OAUTH2_PROXY_CLIENT_*` match the client                                      |
| Browser displays a “Found” link instead of opening sign-in | Ensure shared ForwardAuth points to oauth2-proxy `/`, which returns the login redirect as an actual 302; recreate `oauth2-proxy` after changing its labels                         |
| `oauth2-proxy` cannot discover issuer                      | Check `OAUTH2_PROXY_OIDC_ISSUER_URL` is the issuer base URL, not the well-known URL. For a local issuer through host Traefik, set `OAUTH2_PROXY_OIDC_ISSUER_HOST` to its hostname. |
| UI still public after enabling auth                        | Set both `AUTH_ENABLED=true` and `AUTH_MIDDLEWARE=auth-default`, then `cli/target/release/dss restart --service <folder>`                                                         |
| API clients fail on chromadb/qdrant Traefik hosts          | Auth is opt-in; use `AUTH_MIDDLEWARE=auth-none` for API-first access through the domain and provide native keys such as `QDRANT_API_KEY`                                           |
| Cookie not shared across UIs                               | Cookie domain must be `.sandbox.localhost` (default); browse via HTTPS Traefik hosts, not raw localhost ports                                                                      |
| Do not put gateway in front of the OIDC issuer             | Keep issuer routers without `AUTH_MIDDLEWARE`                                                                                                                                      |

### Common Issues

| Problem                   | Solution                                                                     |
| :------------------------ | :--------------------------------------------------------------------------- |
| Services stuck "starting" | Wait 30-60 seconds, check logs, restart: `dss restart --service <name>`      |
| Can't connect to database | Verify port mapping, check .env passwords, test: `docker-compose ps`         |
| Out of disk space         | Run `cli/target/release/dss prune`, remove images: `docker image prune -a`   |
| Need to reset everything  | Run `cli/target/release/dss teardown` then `make tui`                        |

### Getting Help

```bash
cli/target/release/dss health               # Check service health
docker-compose ps                           # View status
cli/target/release/dss logs --service <name> # View logs

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
1. Check Docker logs: `cli/target/release/dss logs --service <name>`
1. Validate configuration: `make validate`
1. Inspect networks: `docker network inspect traefik_proxy`, `docker network inspect backend_net`, and `docker network inspect data_net`

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Configuration & Networking Guide](configuration.md)
- [Commands & Operations Guide](usage.md)
