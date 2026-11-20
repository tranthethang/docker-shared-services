//! Static service lists, start order, and password rules.

/// Every service directory that ships a `docker-compose.yml`.
pub const SERVICES: &[&str] = &[
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
    "garage_ui",
    "gitea",
    "gotenberg",
    "hasura",
    "host-bridge",
    "hindsight",
    "inngest",
    "jenkins",
    "kafka",
    "libreoffice-writer",
    "litellm",
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
    "verdaccio",
    "woodpecker",
    "zitadel",
];

pub const MANIFEST_FILE: &str = "dss-package.json";

#[derive(serde::Deserialize)]
struct Manifest {
    services: Vec<String>,
}

/// The `SERVICES` entries named in a manifest, in `SERVICES` order. `None` on bad JSON.
pub fn select_services(manifest_json: &str) -> Option<Vec<&'static str>> {
    let manifest: Manifest = serde_json::from_str(manifest_json).ok()?;
    Some(
        SERVICES
            .iter()
            .copied()
            .filter(|s| manifest.services.iter().any(|m| m == s))
            .collect(),
    )
}

/// Services this checkout manages: all of `SERVICES`, or the subset in `dss-package.json`.
pub fn active_services() -> &'static [&'static str] {
    static ACTIVE: std::sync::OnceLock<Vec<&'static str>> = std::sync::OnceLock::new();
    ACTIVE.get_or_init(|| {
        std::fs::read_to_string(MANIFEST_FILE)
            .ok()
            .and_then(|json| select_services(&json))
            .unwrap_or_else(|| SERVICES.to_vec())
    })
}

/// Infra-first order for batch start. Services not listed start by name.
pub const START_ORDER: &[&str] = &[
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
    "litellm",
];

/// Backend -> direct dependents. `dependency_queue` expands this transitively.
pub const PACKAGE_REQUIRES: &[(&str, &[&str])] = &[
    (
        "postgres",
        &[
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
    ),
    ("pgvector", &["hindsight"]),
    ("redis", &["inngest", "redisinsight"]),
    ("garage", &["garage_ui"]),
];

/// Services checked when the package wizard opens.
pub const PACKAGE_DEFAULT_SERVICES: &[&str] = &[
    "traefik",
    "oauth2-proxy",
    "postgres",
    "redis",
    "adminer",
    "mailpit",
    "garage",
];

/// Old repo default password. Legacy `.env` files may hold it, so setup rejects it.
pub const LEGACY_PLACEHOLDER_PASSWORD: &str = "Password102!";
pub const INVALID_PASSWORD_VALUES: &[&str] = &[LEGACY_PLACEHOLDER_PASSWORD];

/// Special characters safe in URLs, shell, `.env`, and compose files.
pub const PASSWORD_SPECIALS: &str = "-_.!*";
pub const PASSWORD_MIN_LENGTH: usize = 15;

/// Service dir -> vars that must pass `validate_password_strength` before `up`.
pub const STRONG_PASSWORD_REQUIRED: &[(&str, &[&str])] =
    &[("zitadel", &["ZITADEL_ADMIN_PASSWORD"])];

/// Return an error message when the password is too weak.
pub fn validate_password_strength(password: &str) -> Option<String> {
    let msg = if password.chars().count() < PASSWORD_MIN_LENGTH {
        format!("Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    } else if !password.chars().any(|c| c.is_ascii_lowercase()) {
        "Password must contain a lowercase letter.".into()
    } else if !password.chars().any(|c| c.is_ascii_uppercase()) {
        "Password must contain an uppercase letter.".into()
    } else if !password.chars().any(|c| c.is_ascii_digit()) {
        "Password must contain a digit.".into()
    } else if password.chars().all(|c| c.is_ascii_alphanumeric()) {
        "Password must contain a special character.".into()
    } else {
        return None;
    };
    Some(msg)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn start_order_entries_are_services() {
        for name in START_ORDER {
            assert!(SERVICES.contains(name), "{name} missing from SERVICES");
        }
    }

    #[test]
    fn traefik_starts_first_and_postgres_before_pgvector() {
        assert_eq!(START_ORDER[0], "traefik");
        let pos = |n| START_ORDER.iter().position(|s| *s == n).unwrap();
        assert!(pos("postgres") < pos("pgvector"));
        assert!(pos("pgvector") < pos("hindsight"));
    }

    #[test]
    fn package_requires_names_are_services() {
        for (backend, deps) in PACKAGE_REQUIRES {
            assert!(SERVICES.contains(backend));
            assert!(deps.iter().all(|d| SERVICES.contains(d)));
        }
    }

    #[test]
    fn manifest_limits_services_in_catalog_order() {
        let json = r#"{"services": ["redis", "traefik", "unknown", "adminer"]}"#;
        assert_eq!(
            select_services(json).unwrap(),
            ["adminer", "redis", "traefik"]
        );
        assert!(select_services("not json").is_none());
        assert_eq!(
            active_services(),
            SERVICES,
            "no manifest in the cli directory"
        );
    }

    #[test]
    fn legacy_password_is_invalid() {
        assert!(INVALID_PASSWORD_VALUES.contains(&"Password102!"));
    }

    #[test]
    fn password_strength_rules() {
        assert!(validate_password_strength("short1A!")
            .unwrap()
            .contains("15"));
        assert!(validate_password_strength("alllowercase1234!x")
            .unwrap()
            .contains("uppercase"));
        assert!(validate_password_strength("ALLUPPERCASE1234!X")
            .unwrap()
            .contains("lowercase"));
        assert!(validate_password_strength("NoDigitsHere-abcdefg")
            .unwrap()
            .contains("digit"));
        assert!(validate_password_strength("NoSpecial1234567890a")
            .unwrap()
            .contains("special"));
        assert_eq!(validate_password_strength("Str0ng-Password-ok!"), None);
    }
}
