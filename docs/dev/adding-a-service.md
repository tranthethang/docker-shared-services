# Adding a service

Steps and rules for a new `<service>/` directory. Each rule names the tool that enforces it. "Review only" means no tool checks it.

## 1. Compose project

Create `<service>/docker-compose.yml` and `<service>/.env.example`.

- Every service is its own Compose project, loaded with `--project-directory <service>` together with `docker-compose.shared.yml`, so `<service>/.env` and relative paths resolve. **Enforced by** `make validate` (runs `docker compose --project-directory <service> -f docker-compose.shared.yml -f <service>/docker-compose.yml config` for each service).
- Attach only the external networks the service needs: `traefik_proxy` for a web UI, `backend_net` for app-to-app traffic, `data_net` for databases. A data store attaches to `data_net` and not `backend_net`; a client joins `data_net` only as a `PACKAGE_REQUIRES` consumer, a same-project container, or a `DATA_CLIENT_UI_SERVICES` entry. See [network segmentation](../network-segmentation.md#data-tier-rules). **Enforced by** `cli/src/repo_rules.rs` (`make test`) for the data tier; the rest is **review only**.
- Pin image tags; do not use `latest`. Set `container_name: ${SANDBOX_NAME:+${SANDBOX_NAME}-}<name>` (the `SANDBOX_NAME` prefix keeps several stacks apart; a fixed volume or network `name:` takes `${SANDBOX_NAME:+${SANDBOX_NAME}_}<name>`; **enforced by** `cli/src/repo_rules.rs`), `restart: "${RESTART_POLICY:-unless-stopped}"`, resource limits through `<SERVICE>_*` env vars, `json-file` logging with rotation, and a `healthcheck` whenever the image allows one. **Review only.**
- Every service sets `restart`. **Enforced by** `cli/src/repo_rules.rs` (`make test`).
- A one-shot init container (for example `garage-config-init`) sets `restart: "no"`, and the main service waits on it with `condition: service_completed_successfully`. A one-shot that must run after the main service is healthy may `depends_on` that service with `condition: service_healthy` instead. `dss up` and the dashboard wait until every `restart: "no"` container exits 0. List it in the catalog `containers` too. **Enforced by** `cli/src/repo_rules.rs` (`make test`), `cli/src/docker/oneshot.rs` on `dss up`, and the catalog check (`make validate`).
- Prefer **no** `ports:` on data-store compose services; Mac TCP uses **`host-bridge`** (`cli/target/release/dss up --service host-bridge`) with aliases documented in [host-bridge/USAGE.md](../../host-bridge/USAGE.md). If a service must publish a host port outside that table, bind to `127.0.0.1` only and document why. **Review only.**
- `depends_on` does not cross Compose projects. Declare cross-project backends in `PACKAGE_REQUIRES` (step 3). **Review only.**
- A service that only reads Docker state uses a `tecnativa/docker-socket-proxy` sidecar on its own internal network, not a direct `docker.sock` mount. See [Docker API access](../network-segmentation.md#docker-api-access). **Review only.**
- `.env.example` ships empty values for secrets, and Compose reads them as `${VAR:?Set VAR in .env — run make setup}` so a missing value stops `up`. Add locally generated secrets to `AUTO_SECRETS` in `cli/src/env/tables.rs`. The legacy password `Password102!` is rejected. **Enforced by** `make setup` (`dss env passwords` refuses it) and `dss up` (the prerequisite check rejects it for variables in `VALIDATION_RULES` in `cli/src/env/tables.rs`).

## 2. Web UI through Traefik

Publish web UIs with Traefik labels, not host ports:

```yaml
labels:
  - "traefik.enable=true"
  - "sandbox.stack=${SANDBOX_NAME:-sandbox}"
  - "traefik.docker.network=${SANDBOX_NAME:+${SANDBOX_NAME}_}traefik_proxy"
  - "traefik.http.routers.<service>.rule=Host(`<service>.${DOMAIN:-sandbox.localhost}`)"
  - "traefik.http.routers.<service>.entrypoints=web"
  - "traefik.http.services.<service>.loadbalancer.server.port=<port>"
```

- Every service with `traefik.enable=true` carries the `sandbox.stack` label, because Traefik only routes containers of its own stack. **Enforced by** `cli/src/repo_rules.rs` (`make test`).
- The host is `<name>.${DOMAIN}` (default `<name>.sandbox.localhost`) over HTTPS via Caddy (Traefik `web` entrypoint, no `tls=true` labels). **Review only.**
- UIs that support the auth gateway take `AUTH_MIDDLEWARE` and are listed in `AUTH_OPT_IN_UI_SERVICES` in `cli/src/env/tables.rs`. **Review only.**

## 3. Register the service in `cli/src/config.rs`

- Add the directory name to `SERVICES`. **Enforced by** `cli/src/repo_rules.rs` (every directory with a `docker-compose.yml` is in `SERVICES` and the catalog).
- If other services start it first, add it to `START_ORDER`. **Review only.**
- Record cross-project backends in `PACKAGE_REQUIRES` (backend → services that need it), for example `postgres` → `zitadel`. `dss up --service <name>` starts and waits on these. **Enforced by** the dependency queue tests in `cli/src/docker/mod.rs` (transitive order). Whether the list is complete is **review only**.
- Add mandatory variables to `VALIDATION_RULES`, generated secrets to `AUTO_SECRETS`, and shared-password keys to `SHARED_PASSWORD_KEYS` in `cli/src/env/tables.rs`. Add the service to the banner table in `cli/src/package/filter.rs` when `.env.example` has a banner for it. **Review only**, except the banner table: a test fails on an unmapped banner.

## 4. Service catalog

Add an entry to `cli/service_catalog.json` with exactly these fields: `category`, `description`, `containers`, `web_ui`, `info`.

- `category` is one of `CATEGORIES` in `cli/src/catalog.rs`. `description` is non-empty. `web_ui` URLs start with `https://`. **Enforced by** `catalog_problems` (`make validate`, and a test with an empty compose map).
- `containers` lists exactly the Compose service names in the stack. **Enforced by** `make validate` (compares with `docker compose config --services`).
- `info` lines are what `dss info` prints, sorted. Edit the catalog, not code, to change them. **Enforced by** the `info` tests in `cli/src/info.rs` (sorting and domain substitution).

## 5. Docs and checks

1. Add the service to `docs/services.md`. **Review only.**
1. Run `make check`.
1. Start it with `cli/target/release/dss up --service <name>` and confirm `cli/target/release/dss health --service <name>`.
