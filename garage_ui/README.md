# Garage Web UI

[garage-webui](https://github.com/khairul169/garage-webui) dashboard for the **garage** S3 cluster in this repo.

## URL

- **https://garage-ui.dss.localhost** (Traefik, HTTPS)

## Start

From the repository root:

```bash
make up service=garage_ui
```

`make up` starts **garage** first, then **garage-webui**.

## Admin token

Copy `GARAGE_ADMIN_TOKEN` from `garage/.env` into `garage_ui/.env`. The Web UI uses it as `API_ADMIN_KEY` for the Garage admin API on `http://garage:3903`.

If the token in `garage_ui/.env` does not match `garage/.env`, cluster data will not load in the UI.

## Login (UI auth)

garage-webui uses **`AUTH_USER_PASS`**: a `username:bcrypt_hash` string (not Traefik basic auth).

**Default (after `make setup`):** user **`admin`**, password **`DSS_SHARED_PASSWORD`** from the root `.env` — same as Traefik, Grafana, RabbitMQ, and the other stack UIs.

`make setup` / `fill-shared-password` writes `GARAGE_UI_AUTH_USER_PASS` as a bcrypt line derived from that password (requires `htpasswd` on the host, e.g. macOS `/usr/sbin/htpasswd`).

To use a different password, generate a hash and set `GARAGE_UI_AUTH_USER_PASS` manually (escape each `$` as `$$` for Docker Compose):

```bash
htpasswd -nbBC 10 "admin" "your-password"
```

## Configuration

Backend URLs are set in `docker-compose.yml`:

- Admin API: `http://garage:3903`
- S3 API: `http://garage:3900`
- Region: `garage`

Garage’s REST admin host (**https://admin.garage.dss.localhost**) stays API-only; use this UI for browser administration.
