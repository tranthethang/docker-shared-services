# LiteLLM (OpenAI-compatible proxy)

[LiteLLM](https://docs.litellm.ai/) proxy with admin UI. Models, virtual keys, and provider
credentials are stored in shared Postgres 16 (`litellm` database). The pinned image is
`ghcr.io/berriai/litellm:v1.106.6` (set `LITELLM_IMAGE` in `.env`; do not use `latest` or
`main-stable`).

| Endpoint              | URL                                |
| --------------------- | ---------------------------------- |
| Admin UI              | `https://litellm.dss.localhost/ui` |
| OpenAI-compatible API | `https://litellm.dss.localhost/v1` |

## Prerequisites

1. Root `.env` and `litellm/.env` (from repo root):

   ```bash
   make setup
   ```

1. Shared Postgres 16 on `data_net`. On a **new** Postgres volume, `postgres/bin/init.sh`
   creates the `litellm` database. On an **existing** volume, create it once:

   ```bash
   make up service=postgres
   docker exec postgres psql -U postgres -c "CREATE DATABASE litellm;"
   ```

1. Traefik for HTTPS (`make up service=traefik`).

## Start

```bash
make up service=litellm
```

Startup runs Prisma migrations from the container entrypoint. A major image upgrade can take
longer on first boot while schema and spend-log indexes are applied. Check logs with
`make logs service=litellm`.

## API smoke test

Create a **virtual key** and a **model** in the Admin UI first. Replace `sk-...` with your
virtual key and `your-model` with the model name shown on the proxy (must be allowed on that
key).

From the host (Traefik):

```bash
curl -sS https://litellm.dss.localhost/v1/chat/completions \
  -H "Authorization: Bearer sk-..." \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Ping"}],"max_tokens":16}'
```

The reply is in `choices[0].message.content` (expect something like `Pong` depending on the
model). From another container on `backend_net`, use `http://litellm:4000/v1/...` instead of
the HTTPS URL.

## Admin UI login (bootstrap)

By default this stack does **not** set `UI_USERNAME` or `UI_PASSWORD`. LiteLLM then accepts:

| Field    | Value                                                 |
| -------- | ----------------------------------------------------- |
| Username | `admin` (LiteLLM default when `UI_USERNAME` is unset) |
| Password | `LITELLM_MASTER_KEY` from `litellm/.env`              |

Anyone who knows the master key can sign in as a **proxy admin**. The API also accepts the
master key as a Bearer token; that behavior is unchanged when env login is disabled.

`LITELLM_SALT_KEY` encrypts provider API keys saved in the UI. **Do not change it** after
keys are stored, or existing provider credentials become unreadable.

## “Environment-credential login is enabled” banner

From LiteLLM v1.106.x, the dashboard shows a warning while login via `UI_USERNAME` /
`UI_PASSWORD` (or the master key when `UI_PASSWORD` is unset) remains allowed. This is a
**security reminder**, not an error. LiteLLM treats that path as bootstrap-only: one shared
secret, no per-person rotation, and audit logs cannot attribute UI actions to an individual.

For local dev with a single operator, you can ignore the banner and keep using `admin` +
`LITELLM_MASTER_KEY`.

To turn the env login path off (recommended when several people use the UI or the host is
shared):

1. Sign in with `admin` and `LITELLM_MASTER_KEY`.

1. **Internal Users** → **+ Invite User** → role **proxy_admin** → set a password via the
   invite link (or `POST /user/new` with `user_role: proxy_admin`).

1. Sign out and confirm login with the new email and password.

1. Add to `config.yaml`:

   ```yaml
   general_settings:
     disable_env_credential_login: true
   ```

1. Restart: `make restart service=litellm`.

After restart, `admin` + master key are rejected on the UI login page; database users (and
SSO, if configured) still work. The master key continues to work for `/v1` API calls.

**Do not** set `disable_env_credential_login: true` before at least one `proxy_admin` user
with a password exists, or you will lock yourself out of the UI. To recover, remove the
setting from `config.yaml` and restart.

Optional env overrides (not set in this repo by default):

```env
UI_USERNAME=admin
UI_PASSWORD=your-ui-only-password
```

If `UI_PASSWORD` is set, the UI password is no longer the master key, but env login is still
shared static credentials until disabled as above.

## Configuration

- `config.yaml` — proxy settings (models are added in the UI when `store_model_in_db: true`).
- `litellm/.env` — image pin, Postgres password, `LITELLM_MASTER_KEY`, `LITELLM_SALT_KEY`.

See also [docs/services.md](../docs/services.md) and
[LiteLLM upgrade guide](https://docs.litellm.ai/docs/proxy/upgrade_guide).
