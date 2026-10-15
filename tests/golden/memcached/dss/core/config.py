SERVICES = [
    'memcached',
]

ACTIONS = ["up", "down", "stop", "restart", "logs"]

# Infra-first startup order for batch manage (services not listed start/stop by name).
# "postgres" (16) is the default shared DB backend other services depend on, so it
# starts early. "pgvector" (Postgres 17 + vector) is the backend for Hindsight and
# starts before consumers that need it.
START_ORDER = [
    'memcached',
]

VALIDATION_RULES = {}

# Local random secrets that `make setup` can auto-fill when empty.
# Format: service -> { VAR: (method, nbytes) } where method is "hex", "base64", "htpasswd",
# or "jwt_hs256" (signed with JWT_SECRET from the same .env; nbytes unused).
# External API keys (e.g. HINDSIGHT_API_LLM_API_KEY) stay manual.
# These stay UNIQUE per variable (not the shared password).
AUTO_GENERATED_SECRETS = {}

# UI services that can attach Traefik middleware auth-default / auth-admin.
# Public (default): AUTH_MIDDLEWARE=auth-none (or unset → compose default auth-none).
AUTH_GATEWAY_MIDDLEWARE_OFF = "auth-none"
AUTH_GATEWAY_MIDDLEWARES_ON = frozenset({"auth-default", "auth-admin"})
AUTH_OPT_IN_UI_SERVICES = []

# Data-store UIs allowed on data_net besides PACKAGE_REQUIRES consumers (test_network_tiers).
DATA_CLIENT_UI_SERVICES = [
    "adminer",
    "appsmith",
    "chromadb_admin",
    "n8n",
    "node-red",
    "redisinsight",
]

# Sentinel values treated as "still the repo default" and safe to overwrite
# when applying the shared password.
SHARED_PASSWORD_PLACEHOLDERS = frozenset(
    {
        "",
        "change-me-generate-with-openssl-rand-base64-50",
        "replace_with_openssl_rand_hex_32",
    }
)

# Old repo default. Example files now ship empty values, but .env files created
# before that may still hold it, so setup keeps overwriting and rejecting it.
LEGACY_PLACEHOLDER_PASSWORD = "Password102!"  # noqa: S105  # rejected value, not a secret
INVALID_PASSWORD_VALUES = frozenset({LEGACY_PLACEHOLDER_PASSWORD})

# Service dir -> vars that must pass validate_password_strength before `up`.
# Zitadel's default password policy rejects the first admin password without a symbol.
STRONG_PASSWORD_REQUIRED = {}

# One shared password is written to every key listed here (service dir -> vars).
# "." is the repo-root .env. ZITADEL_MASTERKEY is intentionally excluded (must
# be exactly 32 chars; the shared password is not that shape).
SHARED_PASSWORD_KEYS: dict[str, list[str]] = {
    '.': ['DSS_SHARED_PASSWORD'],
}

# Values that embed the shared password (not a plain KEY=password assignment).
# Format string receives password=...
SHARED_PASSWORD_TEMPLATES: dict[tuple[str, str], str] = {}

SERVICE_INFO_VARS = {}

# Services checked when the package wizard opens.
PACKAGE_DEFAULT_SERVICES = [
    "traefik",
    "oauth2-proxy",
    "postgres",
    "redis",
    "adminer",
    "mailpit",
    "garage",
]

# Backend -> services that require it. Resolution is transitive, then ordered as SERVICES.
# Zitadel's optional Redis cache URL does not require redis. Woodpecker and Supabase
# do not require postgres. A compose file with traefik.enable=true also requires traefik.
PACKAGE_REQUIRES: dict[str, list[str]] = {
    "postgres": [
        "bugsink",
        "concourse",
        "gitea",
        "hasura",
        "inngest",
        "jenkins",
        "litellm",
        "sonarqube",
        "temporal",
        "zitadel",
    ],
    "pgvector": ["hindsight"],
    "redis": ["inngest", "redisinsight"],
}
