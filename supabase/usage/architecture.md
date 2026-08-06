# Architecture

This service under **docker-shared-services** ships a **pruned** self-hosted Supabase stack: identity, catalog data, file assets, and Realtime — without PostgREST, Edge Functions, or the analytics pipeline.

Postgres here is a **dedicated** `supabase/postgres` container. It does not share data with the repo’s `pgvector` (host `5432`) or `postgres` (host `5433`) stacks.

## Services

| Compose service    | Container                        | Role                                                                       |
| ------------------ | -------------------------------- | -------------------------------------------------------------------------- |
| `supabase-db`      | `supabase-db`                    | PostgreSQL 17 — Auth/Storage metadata and application schemas              |
| `supabase-auth`    | `supabase-auth`                  | GoTrue — email/password, OAuth/SSO hooks, JWT issuance                     |
| `supabase-storage` | `supabase-storage`               | Object storage API (local file backend by default)                         |
| `realtime`         | `realtime-dev.supabase-realtime` | Elixir Realtime — postgres_changes, broadcast, presence                    |
| `supabase-meta`    | `supabase-meta`                  | postgres-meta — schema introspection for Studio                            |
| `supabase-studio`  | `supabase-studio`                | Web dashboard                                                              |
| `supabase-kong`    | `supabase-kong`                  | API gateway (routes, CORS, key-auth, dashboard basic-auth) + Traefik entry |

The Realtime container name **must** stay `realtime-dev.supabase-realtime`: the service derives its tenant id from the `realtime-dev` subdomain.

```
                    ┌─────────────┐
  Browser / SDK ──► │ Traefik     │
  supabase.localhost│ (infra)     │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │    Kong     │──► Studio (:3000)
                    │  :8000/8443 │──► Auth  (:9999)
   host :8002/:8445 └──────┬──────┘──► Storage (:5000)
                           │         ──► Realtime (:4000)
                           │         ──► Meta (:8080)
                           ▼
                     ┌──────────┐
                     │ Postgres │
                     │  :5432   │  (host: SUPABASE_DB_PORT=5434)
                     └──────────┘
```

## What was removed

Compared to the full upstream Docker self-hosting layout, this stack intentionally omits:

- **PostgREST** — no automatic REST API over tables (`/rest/v1`)
- **GraphQL** (`pg_graphql`)
- **Edge Functions** / Deno runtime
- **imgproxy** — image transforms disabled (`ENABLE_IMAGE_TRANSFORMATION=false`)
- **Logflare / Vector** analytics pipeline — Studio Logs Explorer is off
- **Supavisor** connection pooler — Postgres is published on `SUPABASE_DB_PORT` (default `5434`)
- TLS proxy overlays (Caddy / Nginx / Envoy compose files) — Traefik in this repo handles TLS

Use this stack when you need Auth + Storage + Realtime + Studio on a small footprint, and you talk to Postgres with your own API or SQL client (no PostgREST).

## Data volumes

| Path                             | Purpose                                                      |
| -------------------------------- | ------------------------------------------------------------ |
| `volumes/db/data`                | Postgres data directory (runtime, gitignored)                |
| `volumes/db/roles.sql`           | Init: role passwords / grants                                |
| `volumes/db/jwt.sql`             | Init: JWT settings from env                                  |
| `volumes/db/auth-owner.sql`      | Init: transfer `auth.uid`/`role`/`email` ownership to GoTrue |
| `volumes/db/storage-grants.sql`  | Init: grant JWT roles to `supabase_storage_admin`            |
| `volumes/db/realtime.sql`        | Init: create `_realtime` + `realtime` schemas for Realtime   |
| `volumes/storage`                | Local file-backend objects (runtime, gitignored)             |
| `volumes/api/kong.yml`           | Kong declarative routes                                      |
| `volumes/api/kong-entrypoint.sh` | Env substitution into Kong config                            |
| `volumes/snippets`               | Studio SQL snippets mount                                    |

Named Docker volume `supabase_db_config` holds Postgres custom config (including pgsodium key material) across restarts.

Init SQL under `volumes/db/*.sql` runs only on **first** database initialization (empty data dir). See [Troubleshooting](./troubleshooting.md) for already-initialized databases.

Realtime stores its tenant metadata in the `_realtime` schema (created/seeded on first start via `SEED_SELF_HOST=true`).

## Networks

All services join external networks `infra_shared` and `dev_tools` (same as other stacks in this repo). Kong registers the alias `api-gw` on `infra_shared` so other containers can reach the gateway by that name.

Traefik labels on `supabase-kong` use `Host(\`${SUPABASE_SUBDOMAIN}.${DOMAIN_NAME}\`)`(default`supabase.localhost`) on entrypoints `web`/`websecure\`.
