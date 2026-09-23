# Docker Shared Services

![Docker Shared Services](assets/repo.png)

A collection of Docker Compose configurations for 30+ commonly used local development services (databases, caches, message queues, CI/CD, monitoring, auth...), managed centrally through a single `Makefile` and Python scripts in `bin/`.

> [!IMPORTANT]
> **OS Compatibility:** This repository is designed and tested exclusively on **macOS** and **Linux**, since it relies on Unix-style tools/scripts (bash, `ifconfig`, `mkcert`...). **Windows is not supported** (it may work through WSL2, but that hasn't been tested thoroughly).

## 🎯 Why use this repo?

To be upfront: this is not a complete "platform" or a production-ready product — it's a personal/small-team collection of Docker Compose files for quickly spinning up a local dev environment, gathered in one place so you don't have to remember every `docker compose` command for every service. A few reasons to consider it:

- **You don't have to assemble everything from scratch**: 30+ services (Postgres, MySQL, MongoDB, Redis, RabbitMQ, Gitea, Jenkins, Zitadel, Grafana...) already come with a `docker-compose.yml` + `.env.example`, so you don't need to hunt down images or set up networking and healthchecks for each one yourself.
- **A single Makefile** to start/stop, view logs, and check status instead of typing out long `docker compose -f ... -f ... -f ...` commands for each combination of services.
- **Networking is already worked out**: two networks, `infra_shared` and `dev_tools`, with non-overlapping subnets, plus Traefik + `*.dss.localhost` so you can access services by domain name instead of memorizing ports.
- **Pick only the services you need**: `make up` or `make manage` let you start individual services instead of running everything at once (which eats up your dev machine's RAM/CPU).
- **You're in control of the configuration**: default passwords, resource limits, ports, etc. can all be adjusted through each service's `.env` file — there's no hidden "magic", it's all plain YAML and environment variables.

What this repo does **not** do for you: it doesn't perform a security audit, it doesn't tune resource limits for weaker machines, and **the default passwords/configuration in `.env.example` are for local development only — they should never be used as-is in production or on any machine reachable from the internet**. If you need a production-grade stack, treat this repo as a starting reference for configuration, not something to deploy verbatim.

## 🚀 Quick Start

### Setup (about 5 minutes)

```bash
# 1. Create .env files, shared networks, and local SSL certificates
make setup

# 2. Start services (interactive prompt lets you choose 'all' or a specific service)
make up

# 3. Check status
make ps
```

`make setup` will ask you a few yes/no questions along the way (create `.env` from `.env.example`? generate SSL certificates?) — answer `y`/`n` based on your needs; none of the steps are mandatory on the first run.

### Alternative: use Docker Compose directly

If you'd rather skip the Makefile, you can combine compose files manually (for example, to run only pgvector, redis, and otel):

```bash
docker compose -f docker-compose.shared.yml \
  -f pgvector/docker-compose.yml \
  -f redis/docker-compose.yml \
  -f otel/docker-compose.yml \
  up -d
```

Under the hood, the Makefile does essentially the same thing (it automatically `find`s every `docker-compose.yml` in the repo and combines them), so using `make` is still more convenient for most cases.

______________________________________________________________________

## 🔧 Makefile Commands

Run `make help` (or just `make` with no arguments) to see the full list right in your terminal. The tables below go into more detail on each command, including which ones accept a `service=` argument.

### Setup & configuration

| Command              | Description                                                                                                                                                                                                                                                                                                         |
| :------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `make setup`         | Run once when you first clone the repo: creates the two Docker networks (`infra_shared`, `dev_tools`), checks/creates `.env` files from `.env.example`, generates a default Dozzle users file, and (optionally) generates SSL certificates. Safe to re-run — steps that are already done are skipped automatically. |
| `make cert`          | Generates SSL certificates for Traefik using `mkcert` (you need `mkcert` installed first — see `docs/configuration.md`). Certificates are stored in `traefik/certs/` and are not committed to git.                                                                                                                  |
| `make validate`      | Validates the syntax/configuration of every `docker-compose.yml` file in the repo. Worth running after editing a service's compose file.                                                                                                                                                                            |
| `make remove-config` | Removes `.env` files (only ones that have a matching `.env.example`) — use this to "reset" configuration back to defaults. Asks for confirmation before deleting.                                                                                                                                                   |

### Running services (all support a `service=<folder_name>` argument)

| Command        | Description                                                                                                                                                                                                                                    |
| :------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make up`      | Starts services. Running `make up` with no argument shows a prompt to choose "all" or a specific service; `make up service=pgvector` starts that service directly (the service name is its folder name, e.g. `pgvector`, `redis`, `gitea`...). |
| `make down`    | Stops and **removes containers** (does not remove volumes/data) for the selected service, or all services if `service=` is omitted.                                                                                                            |
| `make stop`    | Stops containers but keeps them (does not remove them), so restarting is faster than a full `up`.                                                                                                                                              |
| `make restart` | Restarts a running service. Use this after changing environment variables in `.env` so the container picks up the new config.                                                                                                                  |
| `make logs`    | Shows logs. Without `service=` you'll be prompted to pick one; `make logs service=gitea` shows Gitea's logs specifically.                                                                                                                      |
| `make manage`  | An interactive multi-select menu (arrow keys + space to toggle): checked services are started, unchecked ones are stopped. Handy for quickly switching from "5 services running" to "just these 2 different ones".                             |
| `make ps`      | Shows the status (running/stopped) of every service wired into `docker-compose.shared.yml`.                                                                                                                                                    |
| `make health`  | Shows healthcheck status. `make health service=pgvector` shows it for a single service that has a healthcheck configured.                                                                                                                      |
| `make info`    | Prints the full list of services with their access URLs/ports — handy for quickly checking "what port is Grafana on" without reopening the README.                                                                                             |

### Cleanup (be careful — these can delete data)

| Command           | Description                                                                                                                                                                                                                |
| :---------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `make remove-all` | ⚠️ **Removes all containers AND volumes** (i.e. deletes all data for every service: databases, uploaded files, etc.). Asks for confirmation (`y/n`) before running. Only use this when you're sure you want a clean slate. |
| `make prune`      | Runs `docker system prune -f --volumes` to clean up unused images/containers/volumes (affects your entire Docker install, not just this repo) — frees up disk space.                                                       |

### For contributors / editing code in this repo

| Command             | Description                                                                                                                           |
| :------------------ | :------------------------------------------------------------------------------------------------------------------------------------ |
| `make sync`         | Installs the Python dependencies used for code formatting (`ruff`, `yamlfix`, `mdformat`...) via `uv`. Requires `uv` to be installed. |
| `make format`       | Formats all YAML, JSON, Markdown, Python, and `.env.example` files in the repo to a consistent style.                                 |
| `make format-check` | Same as `make format` but only checks formatting without writing changes — useful in CI or before committing.                         |

> 💡 For commands that accept `service=`, the service name is the **subfolder name** at the repo root (e.g. `pgvector`, `redis`, `mongodb`, `gitea`...), not the container name or a display name.

______________________________________________________________________

## 📚 Further Documentation

For more detail on individual services, network configuration, or troubleshooting, see:

- **[Services & Access Reference](docs/services.md)**: catalog of all services, ports, and default credentials.
- **[Configuration & Networking Guide](docs/configuration.md)**: how to change environment variables, ports, passwords, resource limits, Docker networking, and SSL/TLS certificates.
- **[Commands & Operations Guide](docs/usage.md)**: full Makefile command reference, plain Docker Compose examples, cleanup procedures, and a few development tips.
- **[Troubleshooting & Support](docs/troubleshooting.md)**: common startup issues, port conflicts, out-of-memory errors, and diagnostic steps.

______________________________________________________________________

## 📋 Project Structure

```
docker-shared-services/
├── docker-compose.shared.yml      # Shared network definitions (infra_shared, dev_tools)
├── docs/                          # Detailed documentation
│   ├── services.md
│   ├── configuration.md
│   ├── usage.md
│   └── troubleshooting.md
├── Makefile                       # All management commands
├── bin/                           # Python scripts backing the Makefile (env_manager.py, service_manager.py, ...)
├── [service directories]/         # e.g. pgvector/, redis/, mongodb/, gitea/, etc — each has its own docker-compose.yml + .env.example
```

______________________________________________________________________

## ⚠️ Security Notice

The default passwords and configuration in the `.env.example` files (e.g. `Password102!`) are meant for **local development only** and are not designed to be safe for production environments or any machine reachable from the internet. If you plan to expose a service beyond your local network, change the passwords, restrict network access, and review each service's security configuration first.

______________________________________________________________________

## 🤝 Contributing & Support

- Running into issues? Check the [troubleshooting guide](docs/troubleshooting.md) first.
- Contributions are welcome — feel free to open an issue or pull request if something is missing or incorrect.
- License: see the [LICENSE](LICENSE) file.

______________________________________________________________________

**Docker Version Required**: 20.10+ | **Docker Compose Version Required**: 2.0+
