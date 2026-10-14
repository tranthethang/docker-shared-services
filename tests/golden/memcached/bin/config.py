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
# Format: service -> { VAR: (method, nbytes) } where method is "hex" or "base64" or "htpasswd".
# External API keys (e.g. HINDSIGHT_API_LLM_API_KEY) stay manual.
# These stay UNIQUE per variable (not the shared password).
AUTO_GENERATED_SECRETS = {}

# UI services that can attach Traefik middleware auth-default / auth-admin.
# Public (default): AUTH_MIDDLEWARE=auth-none (or unset → compose default auth-none).
AUTH_GATEWAY_MIDDLEWARE_OFF = "auth-none"
AUTH_GATEWAY_MIDDLEWARES_ON = frozenset({"auth-default", "auth-admin"})
AUTH_OPT_IN_UI_SERVICES = []

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
LEGACY_PLACEHOLDER_PASSWORD = "Password102!"
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
    "zitadel",
    "redis",
    "adminer",
    "mailpit",
    "garage",
    "hasura",
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
    "zitadel": ["oauth2-proxy"],
}


def direct_dependencies(service: str, available: set[str] | None = None) -> list[str]:
    """Backends ``service`` must reach before it starts. ``available`` limits the set."""
    backends: list[str] = []
    for backend, consumers in PACKAGE_REQUIRES.items():
        if service not in consumers or backend == service:
            continue
        if available is not None and backend not in available:
            continue
        backends.append(backend)
    order_map = {name: index for index, name in enumerate(START_ORDER)}
    return sorted(set(backends), key=lambda name: (order_map.get(name, 999), name))


def dependency_queue(service: str, available: set[str] | None = None) -> list[str]:
    """Transitive backends that must be ready before ``service``, in startup order."""
    seen: list[str] = []

    def walk(name: str) -> None:
        for dep in direct_dependencies(name, available):
            if dep in seen:
                continue
            walk(dep)
            seen.append(dep)

    walk(service)
    return startup_queue(seen)


def startup_queue(services) -> list[str]:
    """Dependency order, using ``START_ORDER`` when several services are ready together."""
    selected = list(dict.fromkeys(services))
    selected_set = set(selected)
    deps = {
        name: [dep for dep in direct_dependencies(name) if dep in selected_set] for name in selected
    }
    order_map = {name: index for index, name in enumerate(START_ORDER)}
    remaining = set(selected)
    queued: list[str] = []
    while remaining:
        ready = [name for name in remaining if all(dep not in remaining for dep in deps[name])]
        if not ready:
            queued.extend(sorted(remaining, key=lambda name: (order_map.get(name, 999), name)))
            break
        ready.sort(key=lambda name: (order_map.get(name, 999), name))
        chosen = ready[0]
        queued.append(chosen)
        remaining.remove(chosen)
    return queued
