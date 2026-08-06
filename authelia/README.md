# Authelia

Lightweight SSO / ForwardAuth portal for Traefik-protected admin UIs (replaces HTTP Basic Auth popups).

| Resource         | URL / value                |
| ---------------- | -------------------------- |
| Portal (Traefik) | https://auth.dss.localhost |
| Direct port      | http://localhost:9091      |
| Default user     | `admin` / `password102`    |

## Why `*.dss.localhost`?

Browsers and Authelia **reject session cookies on bare `localhost`**. SSO needs a parent domain with a dot, so this stack uses:

- Cookie domain: `dss.localhost`
- Portal: `auth.dss.localhost`
- Protected apps: `*.dss.localhost` (e.g. `studio.dss.localhost`)

Ensure TLS covers the namespace (`make cert` includes `*.dss.localhost`).

## Start

```bash
# From repo root
cp authelia/.env.example authelia/.env
cp authelia/config/users_database.yml.example authelia/config/users_database.yml

# Generate secrets (≥64 chars each) into authelia/.env
docker run --rm authelia/authelia:4.39.4 \
  authelia crypto rand --length 64 --charset alphanumeric

# Generate Argon2 hash for admin password and paste into users_database.yml
docker run --rm authelia/authelia:4.39.4 \
  authelia crypto hash generate argon2 --password 'password102'

make cert                 # if certs are missing / outdated
make up service=traefik
make up service=authelia
```

Open https://auth.dss.localhost and sign in.

## Protect a service (ForwardAuth)

1. Host the app under `*.dss.localhost` (same cookie parent).
1. Attach the middleware registered by this stack:

```yaml
labels:
  - "traefik.http.routers.<router>.rule=Host(`app.dss.localhost`)"
  - "traefik.http.routers.<router>.middlewares=authelia@docker"
```

3. Disable any existing Basic Auth on that route (e.g. Kong dashboard plugin) to avoid double login.

### Example: Supabase Studio (wired in this repo)

Already configured on `supabase-kong`:

- Studio: https://studio.dss.localhost → middleware `authelia@docker`
- APIs: https://supabase.localhost (`/auth`, `/storage`, `/realtime`, …) — no Authelia
- Legacy Studio URL on `supabase.localhost` redirects to `studio.dss.localhost`
- Kong dashboard `basic-auth` is commented out in `supabase/volumes/api/kong.yml`

Start both stacks: `make up service=authelia` then `make up service=supabase`.

## Users & secrets

Committed templates only — never commit real secrets:

- Users template: `config/users_database.yml.example` → copy to `users_database.yml` (gitignored)
- Env template: `.env.example` → copy to `.env` (gitignored)

Hash a password:

```bash
docker run --rm authelia/authelia:4.39.4 \
  authelia crypto hash generate argon2 --password 'your-password'
```

Secrets in `.env` (`AUTHELIA_JWT_SECRET`, `AUTHELIA_SESSION_SECRET`, `AUTHELIA_STORAGE_ENCRYPTION_KEY`):

```bash
docker run --rm authelia/authelia:4.39.4 \
  authelia crypto rand --length 64 --charset alphanumeric
```

If you change cookie domain / portal URL, update `config/configuration.yml` to match.

## Files

```
authelia/
├── docker-compose.yml
├── .env.example
├── config/
│   ├── configuration.yml              # Authelia settings
│   └── users_database.yml.example     # File-based users template
└── README.md
```
