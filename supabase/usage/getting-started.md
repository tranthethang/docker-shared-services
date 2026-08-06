# Getting Started

Spin up a self-hosted **minimal Supabase** stack: Auth, Postgres, Storage, and Studio behind Kong — on this repo’s shared Docker networks and Traefik.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (`docker compose`)
- Shared networks from repo root: `make setup`
- `openssl` (used by key-generation scripts)
- Optional: `make up service=mailpit` for auth confirmation emails
- Optional: Node.js ≥ 16 (for asymmetric API keys; Docker can substitute)

## First-time setup

```sh
# From repo root
cp supabase/.env.example supabase/.env
(cd supabase && sh utils/generate-keys.sh --update-env)

# Optional but recommended for email auth flows
make up service=mailpit

make up service=supabase
```

Or from `supabase/`:

```sh
cp .env.example .env
sh utils/generate-keys.sh --update-env
sh run.sh start
```

Wait until containers are healthy, then open Studio:

| Resource | URL |
|----------|-----|
| Studio / gateway (Traefik) | https://supabase.localhost |
| Studio / gateway (host) | http://localhost:8002 |
| Auth API | https://supabase.localhost/auth/v1 |
| Storage API | https://supabase.localhost/storage/v1 |
| Postgres | `localhost:5434` |

Studio is protected by **HTTP basic auth** using `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` from `.env` (defaults: `admin` / `password102`).

## Verify the stack

```sh
make ps
# or from supabase/:
sh run.sh status
sh run.sh logs
sh run.sh logs supabase-auth
```

## Client apps

```ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://supabase.localhost',
  process.env.ANON_KEY! // or SUPABASE_PUBLISHABLE_KEY if using opaque keys
)
```

## Next steps

- [Architecture](./architecture.md) — what is included and what was removed
- [Configuration](./configuration.md) — environment variables
- [Secrets and keys](./secrets-and-keys.md) — rotation and asymmetric keys
- [Operations](./operations.md) — day-to-day management with `run.sh`
