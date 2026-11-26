//! Static tables for validation, secret generation, and the shared password.

type Table<T> = &'static [(&'static str, T)];

/// Service dir -> vars that must be set before `up`.
pub const VALIDATION_RULES: Table<&[&str]> = &[
    ("garage", &["GARAGE_RPC_SECRET", "GARAGE_ADMIN_TOKEN"]),
    (
        "garage_ui",
        &["GARAGE_ADMIN_TOKEN", "GARAGE_UI_AUTH_USER_PASS"],
    ),
    ("hasura", &["HASURA_GRAPHQL_ADMIN_SECRET"]),
    ("hindsight", &["HINDSIGHT_API_LLM_API_KEY"]),
    ("inngest", &["INNGEST_EVENT_KEY", "INNGEST_SIGNING_KEY"]),
    (
        "litellm",
        &[
            "LITELLM_MASTER_KEY",
            "LITELLM_SALT_KEY",
            "POSTGRES16_PASSWORD",
        ],
    ),
    ("minio", &["MINIO_ROOT_PASSWORD"]),
    ("mongodb", &["MONGO_ROOT_PASSWORD"]),
    ("mysql8", &["MYSQL_ROOT_PASSWORD"]),
    ("oauth2-proxy", &["OAUTH2_PROXY_COOKIE_SECRET"]),
    ("pgvector", &["PGVECTOR_PASSWORD"]),
    ("postgres", &["POSTGRES16_PASSWORD"]),
    ("rabbitmq", &["RABBITMQ_PASSWORD"]),
    ("traefik", &["TRAEFIK_DASHBOARD_AUTH"]),
    ("verdaccio", &["VERDACCIO_PASSWORD"]),
    ("woodpecker", &["WOODPECKER_AGENT_SECRET"]),
    ("zitadel", &["ZITADEL_MASTERKEY"]),
];

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum Method {
    Hex,
    Base64,
    Htpasswd,
    JwtHs256,
}

/// Secrets `setup` fills when empty: service -> (VAR, method, nbytes).
pub const AUTO_SECRETS: Table<&[(&str, Method, usize)]> = &[
    (".", &[("TRAEFIK_DASHBOARD_AUTH", Method::Htpasswd, 16)]),
    ("bugsink", &[("BUGSINK_SECRET_KEY", Method::Base64, 50)]),
    (
        "garage",
        &[
            ("GARAGE_RPC_SECRET", Method::Hex, 32),
            ("GARAGE_ADMIN_TOKEN", Method::Base64, 32),
        ],
    ),
    (
        "inngest",
        &[
            ("INNGEST_EVENT_KEY", Method::Hex, 8),
            ("INNGEST_SIGNING_KEY", Method::Hex, 8),
        ],
    ),
    (
        "litellm",
        &[
            ("LITELLM_MASTER_KEY", Method::Hex, 32),
            ("LITELLM_SALT_KEY", Method::Hex, 32),
        ],
    ),
    (
        "oauth2-proxy",
        &[("OAUTH2_PROXY_COOKIE_SECRET", Method::Hex, 16)],
    ),
    (
        "supabase",
        &[
            ("JWT_SECRET", Method::Hex, 32),
            ("SECRET_KEY_BASE", Method::Base64, 48),
            ("REALTIME_DB_ENC_KEY", Method::Hex, 8),
            ("PG_META_CRYPTO_KEY", Method::Hex, 32),
            ("S3_PROTOCOL_ACCESS_KEY_ID", Method::Hex, 16),
            ("S3_PROTOCOL_ACCESS_KEY_SECRET", Method::Hex, 32),
            ("ANON_KEY", Method::JwtHs256, 0),
            ("SERVICE_ROLE_KEY", Method::JwtHs256, 0),
        ],
    ),
    (
        "traefik",
        &[("TRAEFIK_DASHBOARD_AUTH", Method::Htpasswd, 16)],
    ),
    (
        "woodpecker",
        &[("WOODPECKER_AGENT_SECRET", Method::Hex, 32)],
    ),
    ("zitadel", &[("ZITADEL_MASTERKEY", Method::Hex, 16)]),
];

/// Values treated as "still the repo default" and safe to overwrite.
pub const SHARED_PASSWORD_PLACEHOLDERS: &[&str] = &[
    "",
    "change-me-generate-with-openssl-rand-base64-50",
    "replace_with_openssl_rand_hex_32",
];

/// Public `.env.example` literals of old installs. Setup warns and keeps them.
pub const KNOWN_SECRET_PLACEHOLDERS: &[&str] = &[
    "MasterkeyNeedsToHave32Characters",
    "change-me-generate-with-openssl-rand-base64-50",
    "00000000000000000000000000000000",
    "your-super-secret-jwt-token-with-at-least-32-characters-long",
    "UpNVntn3cDxHJpq99YMc1T1AQgQpc8kfYTuRgBiYa15BLrx8etQoXz3gZv1/u2oq",
    "supabaserealtime",
    "your-encryption-key-32-chars-min",
    "625729a08b95bf1b7ff351a663f3a23c",
    "850181e4652dd023b7a98c58ae0d2d34bd487ee0cc3254aed6eda37307425907",
];

/// One shared password is written to every key here (service dir -> vars).
pub const SHARED_PASSWORD_KEYS: Table<&[&str]> = &[
    (
        ".",
        &[
            "DSS_SHARED_PASSWORD",
            "POSTGRES16_PASSWORD",
            "PGVECTOR_PASSWORD",
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
    ),
    ("bugsink", &["POSTGRES16_PASSWORD"]),
    ("centrifugo", &["CENTRIFUGO_API_KEY", "JWT_SIGNING_KEY"]),
    ("concourse", &["POSTGRES16_PASSWORD"]),
    ("gitea", &["POSTGRES16_PASSWORD"]),
    (
        "hasura",
        &["POSTGRES16_PASSWORD", "HASURA_GRAPHQL_ADMIN_SECRET"],
    ),
    ("hindsight", &["PGVECTOR_PASSWORD"]),
    ("inngest", &["POSTGRES16_PASSWORD", "REDIS_PASSWORD"]),
    ("jenkins", &["POSTGRES16_PASSWORD"]),
    ("litellm", &["POSTGRES16_PASSWORD"]),
    ("mariadb", &["MARIADB_PASSWORD", "MARIADB_ROOT_PASSWORD"]),
    ("minio", &["MINIO_ROOT_PASSWORD"]),
    ("mongodb", &["MONGO_ROOT_PASSWORD"]),
    ("mysql8", &["MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD"]),
    ("otel", &["GRAFANA_ADMIN_PASSWORD"]),
    ("pgvector", &["PGVECTOR_PASSWORD"]),
    ("postgres", &["POSTGRES16_PASSWORD"]),
    ("qdrant", &["QDRANT_API_KEY"]),
    ("rabbitmq", &["RABBITMQ_PASSWORD"]),
    ("redis", &["REDIS_PASSWORD"]),
    ("sonarqube", &["POSTGRES16_PASSWORD"]),
    ("supabase", &["POSTGRES_PASSWORD", "DASHBOARD_PASSWORD"]),
    (
        "temporal",
        &["POSTGRES16_PASSWORD", "TEMPORAL_S3_SECRET_KEY"],
    ),
    ("verdaccio", &["VERDACCIO_PASSWORD"]),
    (
        "zitadel",
        &["ZITADEL_ADMIN_PASSWORD", "POSTGRES16_PASSWORD"],
    ),
];

/// (service, key, template) values that embed the password as `{password}`.
pub const SHARED_PASSWORD_TEMPLATES: &[(&str, &str, &str)] = &[
    (".", "CONCOURSE_ADD_LOCAL_USER", "admin:{password}"),
    ("concourse", "CONCOURSE_ADD_LOCAL_USER", "admin:{password}"),
    (
        "zitadel",
        "ZITADEL_CACHES_CONNECTORS_REDIS_URL",
        "redis://:{password}@redis:6379/0",
    ),
];

/// (service, key, username) values holding a bcrypt `user:hash` of the password.
pub const SHARED_PASSWORD_BCRYPT: &[(&str, &str, &str)] =
    &[("garage_ui", "GARAGE_UI_AUTH_USER_PASS", "admin")];

/// `.env.example` bcrypt for the password "password". Setup replaces it.
pub const GARAGE_UI_AUTH_PLACEHOLDER: &str =
    "N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy";

pub const SERVICE_INFO_VARS: Table<&[&str]> = &[
    ("bugsink", &["BUGSINK_BASE_URL"]),
    ("centrifugo", &["CENTRIFUGO_PORT"]),
    ("gitea", &["GITEA_SSH_PORT"]),
    ("gotenberg", &["GOTENBERG_API_PORT"]),
    ("hasura", &["HASURA_HOSTNAME"]),
    (
        "hindsight",
        &[
            "HINDSIGHT_HOSTNAME",
            "HINDSIGHT_UI_HOSTNAME",
            "HINDSIGHT_PUBLIC_URL",
            "HINDSIGHT_UI_PUBLIC_URL",
        ],
    ),
    ("libreoffice-writer", &["LIBREOFFICE_WRITER_UNO_PORT"]),
    ("litellm", &["LITELLM_HOSTNAME"]),
    ("mongodb", &["MONGO_PORT"]),
    ("mysql8", &["MYSQL_PORT", "MYSQL_DATABASE"]),
    (
        "oauth2-proxy",
        &["OAUTH2_PROXY_HOSTNAME", "OAUTH2_PROXY_OIDC_ISSUER_URL"],
    ),
    (
        "otel",
        &[
            "OTEL_COLLECTOR_PORT_GRPC",
            "OTEL_COLLECTOR_PORT_HTTP",
            "LOKI_PORT",
        ],
    ),
    ("pgvector", &["PGVECTOR_PORT", "PGVECTOR_DB"]),
    ("postgres", &["POSTGRES16_PORT", "POSTGRES16_DB"]),
    ("redis", &["REDIS_PORT"]),
    (
        "supabase",
        &["SUPABASE_PUBLIC_URL", "SUPABASE_STUDIO_HOSTNAME"],
    ),
    ("temporal", &["TEMPORAL_GRPC_PORT"]),
    ("verdaccio", &["VERDACCIO_PORT", "VERDACCIO_HOSTNAME"]),
    ("zitadel", &["ZITADEL_HOSTNAME"]),
];

pub const AUTH_OPT_IN_UI_SERVICES: &[&str] = &[
    "chromadb",
    "kafka",
    "mermaid-live-editor",
    "qdrant",
    "temporal",
];
pub const AUTH_GATEWAY_MIDDLEWARE_OFF: &str = "auth-none";
pub const AUTH_GATEWAY_MIDDLEWARES_ON: &[&str] = &["auth-default", "auth-admin"];

/// Look up a table row by service name.
pub fn lookup<T: Copy>(table: Table<T>, service: &str) -> Option<T> {
    table
        .iter()
        .find(|(name, _)| *name == service)
        .map(|(_, v)| *v)
}
