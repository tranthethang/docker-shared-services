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

Generate a hash (install `apache2-utils` / `httpd-tools` if `htpasswd` is missing):

```bash
htpasswd -nbBC 10 "admin" "your-password"
```

Put the full line in `garage_ui/.env` as `GARAGE_UI_AUTH_USER_PASS`.

## Configuration

Backend URLs are set in `docker-compose.yml`:

- Admin API: `http://garage:3903`
- S3 API: `http://garage:3900`
- Region: `garage`

Garage’s REST admin host (**https://admin.garage.dss.localhost**) stays API-only; use this UI for browser administration.
