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

### Quality gate

`make check` is the post-change gate. It runs formatting, lint (ruff, file size, shellcheck, shfmt), mypy, pytest, and Compose validation. Compose validation needs env files; CI creates a disposable env before `make check`.

```bash
make check          # format-check, lint, typecheck, test, validate
make test-update    # rewrite tests/golden from export_stack (GOLDEN_UPDATE=1)
```

A normal `make test` compares golden files and does not write them.

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
| `m`                   | Confirm manage plan, then quit and show Docker progress      |
| `?`                   | Help                                                         |
| `q`                   | Quit                                                         |

Notes:

- Status refreshes automatically on Docker container events (start, stop, health changes); `r` forces a refresh.
- `m` closes the dashboard after confirmation and runs the same start/stop commands as `make manage`, so image pulls print in the terminal.
- `oauth2-proxy` is a label until `OAUTH2_PROXY_CLIENT_ID` and `OAUTH2_PROXY_CLIENT_SECRET` are set in `oauth2-proxy/.env`. Space, `a`, `u`, and restart leave it unchanged. Stop and down still work.
- Logs are streamed **unredacted**, exactly like `make logs` / `docker logs`, and only when you press `l`. Application logs can contain credentials; treat the screen accordingly.
- When a Compose action fails, the operations panel shows the last lines of Compose's error output with values from the root and service `.env` files masked as `***`. Run the matching `make` target for the full output.

Setup errors (non-interactive terminal, missing TUI packages, or Docker unreachable) print actionable messages and leave Makefile/CLI workflows available. Every Makefile target that runs Python needs `uv`; without it, Make stops with an install hint.

### Opt-in UI auth (oauth2-proxy)

```bash
make up service=oauth2-proxy
uv run python -m dss.cli.env summary   # AUTH gateway on/off per candidate UI
uv run python -m dss.cli.env merge-missing all   # add keys from .env.example missing in .env
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
