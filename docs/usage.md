# Commands & Operations Guide

> Detailed command references for managing services, performing cleanups, and development pro-tips.

______________________________________________________________________

## 🔧 Usage & Commands

### Makefile (Recommended)

```bash
make help           # Show all commands
make setup          # Setup environment files and shared Docker networks
                    # (also merges new keys from .env.example into existing .env)
make tui            # ratatui dashboard (TTY)
make package        # Package a selected stack into dist/ (TTY wizard)
make build          # Build cli/target/release/dss
make check          # format-check, lint, shell-lint, test, validate
```

### Direct CLI (`cli/target/release/dss`)

For non-interactive or scripted operations after `make build`:

```bash
cli/target/release/dss up --service <name>       # Start one service (and its backends)
cli/target/release/dss down --service <name>     # Stop and remove services
cli/target/release/dss stop --service <name>     # Stop services (keep containers)
cli/target/release/dss restart --service <name>  # Restart services
cli/target/release/dss ps                        # Show service status
cli/target/release/dss health                    # Check service health
cli/target/release/dss logs --service <name>     # View logs
cli/target/release/dss info                      # URLs, ports, opt-in UI auth guidance
cli/target/release/dss teardown                  # Remove containers & volumes
```

### Quality gate

`make check` is the post-change gate. It runs `cargo fmt --check`, clippy, `shellcheck`, `cargo test` (which also checks the Compose files and the 300-line limit), and Compose validation. Compose validation needs env files; CI creates a disposable env before `make check`.

```bash
make check          # format-check, lint, shell-lint, test, validate
make build          # build cli/target/release/dss
```

### Dashboard (`make tui` or `dss`)

Keyboard-driven status, health, and logs UI built with ratatui. It runs the same Compose commands as `dss up` / `down` / `stop` / `restart`.

```bash
make tui    # interactive terminal required
```

| Key                | Action                                                       |
| ------------------ | ------------------------------------------------------------ |
| `↑`/`↓` or `j`/`k` | Move selection                                               |
| `/`                | Filter services (`Enter`/`Esc` returns to the list)          |
| `R`                | Force a status refresh (status also auto-updates)            |
| `Enter`            | Show details and stop following logs                         |
| `l`                | Follow live logs (last 200 lines + new); press again to stop |
| `u` / `s` / `r`    | Up / stop / restart selected stack                           |
| `d`                | Down selected stack (confirm)                                |
| `Space`            | Toggle manage selection                                      |
| `a` / `c`          | Select all / clear the manage selection                      |
| `m`                | Confirm and apply the manage plan                            |
| `?`                | Help                                                         |
| `q`                | Quit                                                         |

Notes:

- Status refreshes automatically on Docker container events (start, stop, health changes); `R` forces a refresh.
- `m` shows what will start and stop, then runs it in the background. Compose output appears in the Operations panel.
- `oauth2-proxy` is a label until `OAUTH2_PROXY_CLIENT_ID` and `OAUTH2_PROXY_CLIENT_SECRET` are set in `oauth2-proxy/.env`. Space, `a`, `u`, and restart leave it unchanged. Stop and down still work.
- Logs are streamed **unredacted**, exactly like `dss logs` / `docker logs`, and only when you press `l`. Application logs can contain credentials; treat the screen accordingly.
- Compose output in the Operations panel has values from the root and service `.env` files masked as `***`. Run the matching `cli/target/release/dss` subcommand for the full output.

Without an interactive terminal, the dashboard prints a message and exits. Use `cli/target/release/dss up --service <name>`, `cli/target/release/dss ps`, or `cli/target/release/dss --help` instead. Every Makefile target builds the binary with `cargo` first. Without `cargo`, Make stops with an install hint.

### Opt-in UI auth (oauth2-proxy)

```bash
cli/target/release/dss up --service oauth2-proxy
cli/target/release/dss env summary         # AUTH gateway on/off per candidate UI
cli/target/release/dss env merge-missing   # add keys from .env.example missing in .env
# Enable for one UI: edit <service>/.env → AUTH_ENABLED=true, AUTH_MIDDLEWARE=auth-default
cli/target/release/dss restart --service mermaid-live-editor
```

See [configuration.md](configuration.md#opt-in-oidc-ui-authentication) and [oauth2-proxy/README.md](../oauth2-proxy/README.md).

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
cli/target/release/dss down --all
```

### Stop and remove volumes (delete data)

```bash
cli/target/release/dss teardown
```

### Deep cleanup

```bash
cli/target/release/dss teardown
cli/target/release/dss prune
docker system prune -a --volumes
```

______________________________________________________________________

## 🎯 Pro Tips

1. **Use `make tui` / `dss`** - Easier than raw `docker compose` commands across 30+ stacks.
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
