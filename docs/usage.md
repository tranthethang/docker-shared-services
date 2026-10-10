# Commands & Operations Guide

> Detailed command references for managing services, performing cleanups, and development pro-tips.

______________________________________________________________________

## 🔧 Usage & Commands

### Makefile (Recommended)

```bash
make help           # Show all commands
make setup          # Setup environment files, networks, and certs
                    # (also merges new keys from .env.example into existing .env)
make cert           # Generate SSL certificates
make up             # Start services (interactive or specific)
make down           # Stop and remove services
make stop           # Stop services (keep containers)
make manage         # Interactive multi-select start/stop
make tui            # Optional Textual dashboard (uv + TTY)
make ps             # Show service status
make logs           # View logs
make info           # URLs, ports, opt-in UI auth guidance
make remove-all     # Remove containers & volumes
make restart        # Restart services
```

### Optional Textual dashboard (`make tui`)

Keyboard-driven status/health/logs UI that reuses the same Compose conventions as the Makefile. Does **not** replace `make manage` or other CLI targets.

```bash
uv sync --group tui   # install optional deps (textual, docker SDK)
make tui
```

| Key                   | Action                                                       |
| --------------------- | ------------------------------------------------------------ |
| `↑`/`↓` or `j`/`k`    | Move selection                                               |
| `/`                   | Filter services (`Enter`/`Esc` returns to the list)          |
| `r`                   | Force a status refresh (status also auto-updates)            |
| `Enter`               | Container details (details also follow the cursor)           |
| `l`                   | Follow live logs (last 200 lines + new); press again to stop |
| `u` / `s` / `Shift+R` | Up / stop / restart selected stack                           |
| `d`                   | Down selected stack (confirm)                                |
| `Space`               | Toggle manage selection                                      |
| `m`                   | Apply manage plan (confirm; start/stop order preserved)      |
| `?`                   | Help                                                         |
| `q`                   | Quit                                                         |

Notes:

- Status refreshes automatically on Docker container events (start, stop, health changes); `r` forces a refresh.
- Logs are streamed **unredacted**, exactly like `make logs` / `docker logs`, and only when you press `l`. Application logs can contain credentials; treat the screen accordingly.
- When a Compose action fails, the operations panel shows the last lines of Compose's error output with values from the root and service `.env` files masked as `***`. Run the matching `make` target for the full output.

Setup errors (missing `uv`, non-interactive terminal, or Docker unreachable) print actionable messages and leave Makefile/CLI workflows available.

### Opt-in UI auth (oauth2-proxy)

```bash
make up service=oauth2-proxy
python bin/env_manager.py summary   # AUTH gateway on/off per candidate UI
python bin/env_manager.py merge-missing all   # add keys from .env.example missing in .env
# Enable for one UI: edit <service>/.env → AUTH_ENABLED=true, AUTH_MIDDLEWARE=auth-default
make restart service=mermaid-live-editor
```

See [configuration.md](configuration.md#opt-in-zitadel-ui-authentication) and [oauth2-proxy/README.md](../oauth2-proxy/README.md).

### Docker Compose Direct

```bash
docker compose ps                    # View status
docker compose logs -f               # View logs
docker compose logs -f [service]     # Specific service
docker compose down                  # Stop all
docker compose down -v               # Stop and remove volumes
```

______________________________________________________________________

## 🗑️ Cleanup

### Stop services (keep data)

```bash
make down
```

### Stop and remove volumes (delete data)

```bash
make remove-all
```

### Deep cleanup

```bash
make remove-all
make prune
docker system prune -a --volumes
```

______________________________________________________________________

## 🎯 Pro Tips

1. **Use Makefile** - Easier than docker-compose commands.
1. **Keep backups** of important databases before major changes.
1. **Monitor resources** - Watch with `docker stats`.
1. **Use .env files** - Don't hardcode sensitive values.
1. **Check logs first** - Most issues are revealed in logs.
1. **Use container names** for inter-service communication.
1. **Always use healthchecks** for critical services.

______________________________________________________________________

## 🔗 Quick Links

- [« Back to Main README](../README.md)
- [Services & Access Reference](services.md)
- [Configuration & Networking Guide](configuration.md)
- [Troubleshooting & Support](troubleshooting.md)
