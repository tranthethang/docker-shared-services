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
    "hasura",
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
    "oauth2-proxy",
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
    "oauth2-proxy",
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
    "hasura",
]

VALIDATION_RULES = {
    "garage": ["GARAGE_RPC_SECRET", "GARAGE_ADMIN_TOKEN"],
    "hasura": ["HASURA_GRAPHQL_ADMIN_SECRET"],
    "hindsight": ["HINDSIGHT_API_LLM_API_KEY"],
    "inngest": ["INNGEST_EVENT_KEY", "INNGEST_SIGNING_KEY"],
    "minio": ["MINIO_ROOT_PASSWORD"],
    "mongodb": ["MONGO_ROOT_PASSWORD"],
    "mysql8": ["MYSQL_ROOT_PASSWORD"],
    # Cookie secret only — Zitadel CLIENT_ID / CLIENT_SECRET are opt-in
    # prerequisites when configuring the auth gateway, not general setup.
    "oauth2-proxy": [
        "OAUTH2_PROXY_COOKIE_SECRET",
    ],
    "pgvector": ["POSTGRES_PASSWORD"],
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
    # Cookie encryption only — Zitadel CLIENT_ID / CLIENT_SECRET stay manual.
    "oauth2-proxy": {
        # oauth2-proxy v7 expects the decoded secret value to be exactly
        # 16, 24, or 32 bytes; use 32 hex characters rather than a 32-byte
        # base64 encoding (which is 44 characters and is rejected).
        "OAUTH2_PROXY_COOKIE_SECRET": ("hex", 16),
    },
    "woodpecker": {
        "WOODPECKER_AGENT_SECRET": ("hex", 32),
    },
}

# UI services that can attach Traefik middleware auth-default / auth-admin.
# Public (default): AUTH_MIDDLEWARE=auth-none (or unset → compose default auth-none).
AUTH_GATEWAY_MIDDLEWARE_OFF = "auth-none"
AUTH_GATEWAY_MIDDLEWARES_ON = frozenset({"auth-default", "auth-admin"})
AUTH_OPT_IN_UI_SERVICES = [
    "chromadb",
    "kafka",
    "mermaid-live-editor",
    "qdrant",
    "temporal",
]

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
    "hasura": ["POSTGRES_PASSWORD", "HASURA_GRAPHQL_ADMIN_SECRET"],
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
    "bugsink": ["BUGSINK_BASE_URL"],
    "centrifugo": ["CENTRIFUGO_PORT"],
    "garage": ["GARAGE_S3_PORT", "GARAGE_ADMIN_PORT"],
    "gitea": ["GITEA_SSH_PORT"],
    "gotenberg": ["GOTENBERG_API_PORT"],
    "hasura": ["HASURA_HOSTNAME"],
    "hindsight": [
        "HINDSIGHT_HOSTNAME",
        "HINDSIGHT_UI_HOSTNAME",
        "HINDSIGHT_PUBLIC_URL",
        "HINDSIGHT_UI_PUBLIC_URL",
    ],
    "mongodb": ["MONGO_PORT"],
    "mysql8": ["MYSQL_PORT", "MYSQL_DATABASE"],
    "oauth2-proxy": ["OAUTH2_PROXY_HOSTNAME", "OAUTH2_PROXY_OIDC_ISSUER_URL"],
    "otel": [
        "OTEL_COLLECTOR_PORT_GRPC",
        "OTEL_COLLECTOR_PORT_HTTP",
        "LOKI_PORT",
    ],
    "pgvector": ["POSTGRES_PORT", "POSTGRES_DB"],
    "postgres": ["POSTGRES16_PORT", "POSTGRES16_DB"],
    "redis": ["REDIS_PORT"],
    "supabase": [
        "SUPABASE_PUBLIC_URL",
        "SUPABASE_STUDIO_HOSTNAME",
    ],
    "temporal": ["TEMPORAL_GRPC_PORT"],
    "zitadel": ["ZITADEL_HOSTNAME"],
}
