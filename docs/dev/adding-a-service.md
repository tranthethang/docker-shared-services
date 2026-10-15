# Adding a service

Steps and rules for a new `<service>/` directory. Each rule names the tool that enforces it. "Review only" means no tool checks it.

## 1. Compose project

Create `<service>/docker-compose.yml` and `<service>/.env.example`.

- Every service is its own Compose project, loaded with `--project-directory <service>` together with `docker-compose.shared.yml`, so `<service>/.env` and relative paths resolve. **Enforced by** `make validate` (runs `docker compose --project-directory <service> -f docker-compose.shared.yml -f <service>/docker-compose.yml config` for each service).
- Attach only the external networks the service needs: `traefik_proxy` for a web UI, `backend_net` for app-to-app traffic, `data_net` for databases. See [network segmentation](../network-segmentation.md). **Review only.**
- Pin image tags; do not use `latest`. Set `container_name`, `restart: "${RESTART_POLICY:-unless-stopped}"`, resource limits through `<SERVICE>_*` env vars, `json-file` logging with rotation, and a `healthcheck` whenever the image allows one. **Review only.**
- Bind database and protocol ports to `127.0.0.1` only (`"127.0.0.1:${PORT}:5432"`). **Review only.**
- `depends_on` does not cross Compose projects. Declare cross-project backends in `PACKAGE_REQUIRES` (step 3). **Review only.**
- `.env.example` ships empty values for secrets. The legacy password `Password102!` is rejected. **Enforced by** `make setup` (`fill-shared-password` refuses it) and `make up` (the prerequisite check rejects it for variables in `VALIDATION_RULES`).

## 2. Web UI through Traefik

Publish web UIs with Traefik labels, not host ports:

```yaml
labels:
  - "traefik.enable=true"
  - "traefik.docker.network=traefik_proxy"
  - "traefik.http.routers.<service>.rule=Host(`<service>.dss.localhost`)"
  - "traefik.http.routers.<service>.entrypoints=websecure"
  - "traefik.http.routers.<service>.tls=true"
  - "traefik.http.services.<service>.loadbalancer.server.port=<port>"
```

- The host is `<name>.dss.localhost` over HTTPS. **Review only.**
- UIs that support the auth gateway take `AUTH_MIDDLEWARE` and are listed in `AUTH_OPT_IN_UI_SERVICES` in `dss/core/config.py`. **Review only.**

## 3. Register the service in `dss/core/config.py`

- Add the directory name to `SERVICES`. **Enforced by** `tests/test_service_catalog.py` (every directory with a `docker-compose.yml` is in `SERVICES` and the catalog).
- If other services start it first, add it to `START_ORDER`. **Review only.**
- Record cross-project backends in `PACKAGE_REQUIRES` (backend → services that need it), for example `postgres` → `zitadel`. `make up service=<name>` starts and waits on these. **Enforced by** `tests/test_config.py` (no cycles, transitive order). Whether the list is complete is **review only**.
- Add mandatory variables to `VALIDATION_RULES`, generated secrets to `AUTO_GENERATED_SECRETS`, and shared-password keys to `SHARED_PASSWORD_KEYS`. **Review only.**

Editing `config.py` changes the export goldens. Run `make test-update` and review the diff ([quality-gate.md](quality-gate.md)).

## 4. Service catalog

Add an entry to `dss/core/service_catalog.json` with exactly these fields: `category`, `description`, `containers`, `web_ui`, `info`.

- `category` is one of `CATEGORIES` in `dss/core/service_catalog.py`. `description` is non-empty. `web_ui` URLs start with `https://`. **Enforced by** `catalog_problems` (`make validate`, and `make test` with an empty compose map).
- `containers` lists exactly the Compose service names in the stack. **Enforced by** `make validate` (compares with `docker compose config --services`).
- `info` lines are what `make info` prints, sorted. Edit the catalog, not code, to change them. **Enforced by** `tests/golden/info.txt` (`make test`). Regenerate with `make test-update`.

## 5. Docs and checks

1. Add the service to `docs/services.md`. **Review only.**
1. Run `make check`.
1. Start it with `make up service=<name>` and confirm `make health service=<name>`.
