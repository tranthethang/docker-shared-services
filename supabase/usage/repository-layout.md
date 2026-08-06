# Repository layout

Paths are relative to `supabase/` inside **docker-shared-services**.

```
docker-shared-services/
├── Makefile                    # make up service=supabase, …
├── docker-compose.shared.yml   # external networks infra_shared / dev_tools
└── supabase/
    ├── docker-compose.yml      # Stack definition (6 services)
    ├── .env.example            # Environment template
    ├── .env                    # Local secrets (gitignored)
    ├── run.sh                  # Start / stop / logs / helpers
    ├── reset.sh                # Wipe containers + data
    ├── utils/                  # Key generation & password tools
    │   ├── generate-keys.sh
    │   ├── add-new-auth-keys.sh
    │   ├── rotate-new-api-keys.sh
    │   ├── db-passwd.sh
    │   └── reassign-owner.sh
    ├── volumes/
    │   ├── api/                # Kong config + entrypoint (required)
    │   │   ├── kong.yml
    │   │   └── kong-entrypoint.sh
    │   ├── db/                 # Init SQL (+ runtime data/)
    │   │   ├── roles.sql
    │   │   ├── jwt.sql
    │   │   ├── auth-owner.sql
    │   │   └── data/           # Postgres data (runtime)
    │   ├── snippets/           # Studio SQL snippets
    │   └── storage/            # File-backend objects (runtime)
    └── usage/                  # This documentation
```

## Gitignore notes

Tracked config under `volumes/`:

- `volumes/api/kong.yml`, `volumes/api/kong-entrypoint.sh`
- `volumes/db/roles.sql`, `jwt.sql`, `auth-owner.sql`
- `volumes/snippets/.gitkeep`

Runtime / secret paths must not be committed:

- `supabase/.env`
- `supabase/volumes/db/data`
- `supabase/volumes/storage`
- snippet contents under `supabase/volumes/snippets/` (`.gitkeep` retained)
- `docker-compose.override.yml`

Root `.gitignore` ignores `**/volumes/` and `*.sql` globally, with explicit keep rules for the Supabase config paths above.

## Related repo wiring

| Piece | Role |
|-------|------|
| `bin/config.py` | Lists `supabase` in `SERVICES` / `START_ORDER` |
| `make info` | Prints host port `8002`, Traefik host, DB `5434` |
| Traefik | Routes `supabase.localhost` → Kong |
| Mailpit | Default SMTP for GoTrue (`mailpit:1025`) |
