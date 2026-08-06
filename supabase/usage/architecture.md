# Architecture

This repository ships a **pruned** self-hosted Supabase stack focused on identity, catalog data, and file assets — without Realtime, PostgREST, Edge Functions, or the analytics pipeline.

## Services

| Compose service | Container | Role |
|-----------------|-----------|------|
| `supabase-db` | `supabase-db` | PostgreSQL 17 — Auth/Storage metadata and your application schemas |
| `supabase-auth` | `supabase-auth` | GoTrue — email/password, OAuth hooks, JWT issuance |
| `supabase-storage` | `supabase-storage` | Object storage API (local file backend by default) |
| `supabase-meta` | `supabase-meta` | postgres-meta — schema introspection for Studio |
| `supabase-studio` | `supabase-studio` | Web dashboard |
| `supabase-kong` | `supabase-kong` | API gateway (routes, CORS, key-auth, dashboard basic-auth) + Traefik entry |

```
                    ┌─────────────┐
  Browser / SDK ──► │ Traefik     │
  supabase.localhost│             │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │    Kong     │──► Studio
                    │  :8000/8443 │──► Auth  (:9999)
                    └──────┬──────┘──► Storage (:5000)
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
- **Realtime** — no websocket change feeds
- **GraphQL** (`pg_graphql`)
- **Edge Functions** / Deno runtime
- **imgproxy** — image transforms disabled (`ENABLE_IMAGE_TRANSFORMATION=false`)
- **Logflare / Vector** analytics pipeline — Studio Logs Explorer is off
- **Supavisor** connection pooler — Postgres is published on `SUPABASE_DB_PORT` (default `5434`)
- TLS proxy overlays (Caddy / Nginx / Envoy compose files) — Traefik in this repo handles TLS

Use this stack when you need Auth + Storage + Studio on a small footprint, and you talk to Postgres with your own API or SQL client.

## Data volumes

| Path | Purpose |
|------|---------|
| `volumes/db/data` | Postgres data directory (gitignored) |
| `volumes/db/roles.sql` | Init: role passwords / grants |
| `volumes/db/jwt.sql` | Init: JWT settings from env |
| `volumes/storage` | Local file-backend objects (gitignored) |
| `volumes/api/kong.yml` | Kong declarative routes |
| `volumes/snippets` | Studio SQL snippets mount |

Named Docker volume `supabase_db_config` holds Postgres custom config (including pgsodium key material) across restarts.

## Networks

All services join external networks `infra_shared` and `dev_tools` (same as other stacks in this repo). Kong registers the alias `api-gw` on `infra_shared`.
