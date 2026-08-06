# Repository layout

```
.
├── docker-compose.yml      # Stack definition
├── .env.example            # Environment template
├── run.sh                  # Start / stop / logs / helpers
├── reset.sh                # Wipe containers + data
├── utils/                  # Key generation & password tools
│   ├── generate-keys.sh
│   ├── add-new-auth-keys.sh
│   ├── rotate-new-api-keys.sh
│   ├── db-passwd.sh
│   └── reassign-owner.sh
├── volumes/
│   ├── api/                # Kong config + entrypoint
│   ├── db/                 # Init SQL (+ runtime data/)
│   ├── snippets/           # Studio SQL snippets
│   └── storage/            # File-backend objects (runtime)
└── usage/                  # This documentation
```

Runtime / secret paths are gitignored (see [`.gitignore`](../.gitignore)): `.env`, `volumes/db/data`, `volumes/storage`, and snippet contents under `volumes/snippets/` (`.gitkeep` retained).
