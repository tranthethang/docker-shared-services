# Getting Started

Spin up the **minimal Supabase** stack (Auth, dedicated Postgres, Storage, Realtime, Studio behind Kong) on this repo’s shared Docker networks and Traefik.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with Compose v2 (`docker compose`)
- Shared networks from repo root: `make setup` (creates `infra_shared` and `dev_tools`)
- `openssl` (used by key-generation scripts)
- Optional: `make up service=traefik` for `https://supabase.localhost`
- Optional: `make up service=mailpit` for auth confirmation emails
- Optional: Node.js ≥ 16 (for asymmetric API keys; Docker can substitute)

## First-time setup

```sh
# From repo root
cp supabase/.env.example supabase/.env
(cd supabase && sh utils/generate-keys.sh --update-env)

make up service=traefik
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

`run.sh` always `cd`s to `supabase/` before calling Compose, so you can invoke it via absolute path from elsewhere.

Wait until containers are healthy, then open Studio:

| Resource                   | URL                                    |
| -------------------------- | -------------------------------------- |
| Studio / gateway (Traefik) | https://supabase.localhost             |
| Studio / gateway (host)    | http://localhost:8002                  |
| Auth API                   | https://supabase.localhost/auth/v1     |
| Storage API                | https://supabase.localhost/storage/v1  |
| Realtime                   | https://supabase.localhost/realtime/v1 |
| Postgres                   | `localhost:5434`                       |

Studio is protected by **HTTP basic auth** using `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` from `.env` (defaults: `admin` / `password102`).

## Verify the stack

```sh
make ps
# or from supabase/:
sh run.sh status
sh run.sh logs
sh run.sh logs supabase-auth
sh run.sh logs realtime
```

Compose service names: `supabase-db`, `supabase-auth`, `supabase-storage`, `realtime`, `supabase-meta`, `supabase-studio`, `supabase-kong`.

Realtime’s **container** name is `realtime-dev.supabase-realtime` (required by the Realtime tenant id).

## Client apps

```ts
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'https://supabase.localhost',
  process.env.ANON_KEY! // or SUPABASE_PUBLISHABLE_KEY if using opaque keys
)

// Realtime example (broadcast / postgres_changes / presence)
const channel = supabase
  .channel('room-1')
  .on('broadcast', { event: 'ping' }, (payload) => console.log(payload))
  .subscribe()

await channel.send({ type: 'broadcast', event: 'ping', payload: { ok: true } })
```

**Note:** This stack has no PostgREST (`/rest/v1`). Use Auth + Storage + Realtime via the client, and talk to Postgres with SQL, your own API, or Studio. For `postgres_changes`, enable replication on the relevant tables (publication / replica identity) as in upstream Supabase docs.

## Next steps

- [Architecture](./architecture.md) — what is included and what was removed
- [Configuration](./configuration.md) — environment variables
- [Secrets and keys](./secrets-and-keys.md) — rotation and asymmetric keys
- [Operations](./operations.md) — day-to-day management with `run.sh`
