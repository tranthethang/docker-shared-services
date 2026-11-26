# LiteLLM (OpenAI-compatible proxy)

[LiteLLM](https://docs.litellm.ai/) proxy with admin UI. The pinned image is
`ghcr.io/berriai/litellm:v1.111.0` (set `LITELLM_IMAGE` in `.env`; do not use `latest` or
`main-stable`).

`config.yaml` registers no models and no virtual keys. Add both in the Admin UI after
start. They stay in shared Postgres 16 (`litellm` database) while `store_model_in_db` is
true. Provider API keys belong on each model in the UI. `LITELLM_SALT_KEY` encrypts those
credentials.

| Endpoint              | URL                                    |
| --------------------- | -------------------------------------- |
| Admin UI              | `https://litellm.sandbox.localhost/ui` |
| OpenAI-compatible API | `https://litellm.sandbox.localhost/v1` |

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

In the Admin UI, add a model (with its provider API key) and a virtual key that is allowed
to call that model. Then call the model with that key. The master key is rejected on model
routes.

From the repo root (Traefik), replace the key and model name:

```bash
curl -sS https://litellm.sandbox.localhost/v1/chat/completions \
  -H "Authorization: Bearer sk-your-virtual-key" \
  -H "Content-Type: application/json" \
  -d '{"model":"your-model","messages":[{"role":"user","content":"Ping"}],"max_tokens":16}'
```

The reply is in `choices[0].message.content`. From another container on `backend_net`, use
`http://litellm:4000/v1/...` instead of the HTTPS URL.

## Public docs

`NO_DOCS`, `NO_REDOC`, and `NO_OPENAPI` are set on the container. `/docs`, `/redoc`, and
`/openapi.json` are not served. `/` and `/ui` serve the Admin UI.

## Admin UI login

The Admin UI accepts username `admin` and password `LITELLM_MASTER_KEY` when
`UI_PASSWORD` is unset. The dashboard warning about that login remains, because this
stack keeps the login.

`LITELLM_SALT_KEY` encrypts provider API keys saved in the UI. **Do not change it** after
keys are stored, or existing provider credentials become unreadable.

## Model API keys

Model routes such as `/v1/chat/completions` and `/v1/responses` reject the master key.
Call them with a virtual key created in the Admin UI. The master key still authorizes
admin routes such as `/key/generate`. `reject_master_key_inference.py` enforces the
model-route rejection.

## Configuration

- `config.yaml` — proxy settings only. Models and virtual keys are created in the UI.
- `litellm/.env` — image pin, Postgres password, `LITELLM_MASTER_KEY`, and `LITELLM_SALT_KEY`.
  `make setup` fills empty master and salt keys.

See also [docs/services.md](../docs/services.md) and
[LiteLLM upgrade guide](https://docs.litellm.ai/docs/proxy/upgrade_guide).
