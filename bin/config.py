SERVICES = [
    "act_runner",
    "adminer",
    "appsmith",
    "bugsink",
    "chromadb",
    "chromadb_admin",
    "concourse",
    "crawl4ai",
    "dockge",
    "centrifugo",
    "dozzle",
    "garage",
    "gitea",
    "gotenberg",
    "hindsight",
    "inngest",
    "jenkins",
    "kafka",
    "mailpit",
    "mariadb",
    "memcached",
    "mermaid-live-editor",
    "minio",
    "mongodb",
    "mysql8",
    "n8n",
    "node-red",
    "otel",
    "pgvector",
    "pocketbase",
    "postgres",
    "portainer",
    "qdrant",
    "rabbitmq",
    "redis",
    "redisinsight",
    "sonarqube",
    "supabase",
    "temporal",
    "traefik",
    "woodpecker",
    "zitadel",
]

ACTIONS = ["up", "down", "stop", "restart", "logs"]

# Infra-first startup order for batch manage (services not listed start/stop by name).
# "postgres" (16) is the default shared DB backend other services depend on, so it
# starts early. "pgvector" (Postgres 17 + vector) is the backend for Hindsight and
# starts before consumers that need it.
START_ORDER = [
    "traefik",
    "postgres",
    "pgvector",
    "zitadel",
    "redis",
    "mysql8",
    "mariadb",
    "mongodb",
    "chromadb",
    "qdrant",
    "rabbitmq",
    "memcached",
    "minio",
    "garage",
    "kafka",
    "mailpit",
    "otel",
    "supabase",
    "hindsight",
]

VALIDATION_RULES = {
    "garage": ["GARAGE_RPC_SECRET", "GARAGE_ADMIN_TOKEN"],
    "hindsight": ["HINDSIGHT_API_LLM_API_KEY"],
    "inngest": ["INNGEST_EVENT_KEY", "INNGEST_SIGNING_KEY"],
    "minio": ["MINIO_ROOT_PASSWORD"],
    "mongodb": ["PASSWORD"],
    "mysql8": ["PASSWORD"],
    "pgvector": ["PASSWORD"],
    "postgres": ["POSTGRES16_PASSWORD"],
    "rabbitmq": ["RABBITMQ_PASSWORD"],
    "woodpecker": ["WOODPECKER_AGENT_SECRET"],
    "zitadel": ["ZITADEL_MASTERKEY"],
}

# Local random secrets that `make setup` can auto-fill when empty.
# Format: service -> { VAR: (method, nbytes) } where method is "hex" or "base64".
# External API keys (e.g. HINDSIGHT_API_LLM_API_KEY) stay manual.
# These stay UNIQUE per variable (not the shared password).
AUTO_GENERATED_SECRETS = {
    "garage": {
        "GARAGE_RPC_SECRET": ("hex", 32),
        "GARAGE_ADMIN_TOKEN": ("base64", 32),
    },
    "woodpecker": {
        "WOODPECKER_AGENT_SECRET": ("hex", 32),
    },
}

# Sentinel values treated as "still the repo default" and safe to overwrite
# when applying the shared password.
SHARED_PASSWORD_PLACEHOLDERS = frozenset(
    {
        "",
        "Password102!",
        "change-me-generate-with-openssl-rand-base64-50",
        "replace_with_openssl_rand_hex_32",
    }
)

# One shared password is written to every key listed here (service dir -> vars).
# "." is the repo-root .env. ZITADEL_MASTERKEY is intentionally excluded (must
# be exactly 32 chars; short passwords like Password102! are invalid there).
SHARED_PASSWORD_KEYS: dict[str, list[str]] = {
    ".": [
        "DSS_SHARED_PASSWORD",
        "POSTGRES16_PASSWORD",
        "POSTGRES_PASSWORD",
        "MYSQL_PASSWORD",
        "MYSQL_ROOT_PASSWORD",
        "MARIADB_PASSWORD",
        "MARIADB_ROOT_PASSWORD",
        "MONGO_ROOT_PASSWORD",
        "REDIS_PASSWORD",
        "RABBITMQ_PASSWORD",
        "MINIO_ROOT_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
        "QDRANT_API_KEY",
        "JWT_SIGNING_KEY",
        "CENTRIFUGO_API_KEY",
    ],
    "bugsink": ["POSTGRES_PASSWORD", "BUGSINK_SECRET_KEY"],
    "centrifugo": ["CENTRIFUGO_API_KEY"],
    "concourse": ["POSTGRES_PASSWORD"],
    "gitea": ["POSTGRES_PASSWORD"],
    "hindsight": ["POSTGRES_PASSWORD"],
    "inngest": ["POSTGRES_PASSWORD", "REDIS_PASSWORD"],
    "jenkins": ["POSTGRES_PASSWORD"],
    "mariadb": ["MARIADB_PASSWORD", "MARIADB_ROOT_PASSWORD"],
    "minio": ["MINIO_ROOT_PASSWORD"],
    "mongodb": ["MONGO_ROOT_PASSWORD"],
    "mysql8": ["MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"],
    "otel": ["GRAFANA_ADMIN_PASSWORD"],
    "pgvector": ["POSTGRES_PASSWORD"],
    "postgres": ["POSTGRES16_PASSWORD"],
    "qdrant": ["QDRANT_API_KEY"],
    "rabbitmq": ["RABBITMQ_PASSWORD"],
    "redis": ["REDIS_PASSWORD"],
    "sonarqube": ["POSTGRES_PASSWORD"],
    "supabase": ["POSTGRES_PASSWORD", "DASHBOARD_PASSWORD"],
    "temporal": ["POSTGRES_PWD", "TEMPORAL_S3_SECRET_KEY"],
    "zitadel": ["ZITADEL_ADMIN_PASSWORD", "POSTGRES16_PASSWORD"],
}

# Values that embed the shared password (not a plain KEY=password assignment).
# Format string receives password=...
SHARED_PASSWORD_TEMPLATES: dict[tuple[str, str], str] = {
    (".", "CONCOURSE_ADD_LOCAL_USER"): "admin:{password}",
    ("concourse", "CONCOURSE_ADD_LOCAL_USER"): "admin:{password}",
    ("zitadel", "ZITADEL_CACHES_CONNECTORS_REDIS_URL"): ("redis://:{password}@redis:6379/0"),
}

SERVICE_INFO_VARS = {
    "appsmith": ["APPSMITH_PORT"],
    "bugsink": ["BUGSINK_PORT", "BUGSINK_BASE_URL"],
    "chromadb": ["CHROMADB_PORT"],
    "chromadb_admin": ["CHROMADB_ADMIN_PORT"],
    "centrifugo": ["CENTRIFUGO_PORT"],
    "crawl4ai": ["CRAWL4AI_PORT"],
    "dozzle": ["DOZZLE_PORT"],
    "garage": ["GARAGE_S3_PORT", "GARAGE_ADMIN_PORT"],
    "gitea": ["GITEA_HTTP_PORT", "GITEA_SSH_PORT"],
    "gotenberg": ["GOTENBERG_API_PORT"],
    "hindsight": [
        "HINDSIGHT_HOSTNAME",
        "HINDSIGHT_UI_HOSTNAME",
        "HINDSIGHT_PUBLIC_URL",
        "HINDSIGHT_UI_PUBLIC_URL",
    ],
    "inngest": ["INNGEST_PORT"],
    "mermaid-live-editor": ["MERMAID_LIVE_EDITOR_PORT"],
    "mongodb": ["MONGO_PORT"],
    "mysql8": ["MYSQL_PORT", "MYSQL_DATABASE"],
    "n8n": ["N8N_PORT"],
    "node-red": ["NODE_RED_PORT"],
    "otel": [
        "OTEL_COLLECTOR_PORT_GRPC",
        "OTEL_COLLECTOR_PORT_HTTP",
        "GRAFANA_PORT",
        "LOKI_PORT",
    ],
    "pocketbase": ["POCKETBASE_PORT"],
    "pgvector": ["POSTGRES_PORT", "POSTGRES_DB"],
    "postgres": ["POSTGRES16_PORT", "POSTGRES16_DB"],
    "qdrant": ["QDRANT_HTTP_PORT", "QDRANT_GRPC_PORT"],
    "redis": ["REDIS_PORT"],
    "sonarqube": ["SONARQUBE_PORT"],
    "supabase": [
        "SUPABASE_KONG_HTTP_PORT",
        "SUPABASE_DB_PORT",
        "SUPABASE_PUBLIC_URL",
        "SUPABASE_STUDIO_HOSTNAME",
    ],
    "temporal": ["TEMPORAL_UI_PORT", "TEMPORAL_GRPC_PORT"],
    "woodpecker": ["WOODPECKER_HTTP_PORT"],
    "zitadel": ["ZITADEL_PORT", "ZITADEL_HOSTNAME"],
}
