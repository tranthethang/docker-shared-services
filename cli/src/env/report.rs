//! Validate `.env` files, gate `up`, and print the configuration summary.

use super::tables::*;
use super::{env_path, error, get_services, read_value, success};
use crate::config::{
    validate_password_strength, INVALID_PASSWORD_VALUES, STRONG_PASSWORD_REQUIRED,
};
use std::fs;
use std::path::Path;

/// Report empty, missing, and placeholder required vars. Returns true when all pass.
pub fn validate_env(root: &Path, arg: Option<&str>) -> bool {
    println!("\nValidating environment variables...\n");
    let mut errors = 0;
    for s in get_services(arg) {
        let env = env_path(root, &s);
        if !env.exists() {
            continue;
        }
        for var in lookup(VALIDATION_RULES, &s).unwrap_or(&[]) {
            match read_value(&env, var) {
                None => error(&format!("{s}: Missing {var} variable")),
                Some(v) if v.is_empty() => error(&format!("{s}: {var} is empty (set a value in {s}/.env)")),
                Some(v) if INVALID_PASSWORD_VALUES.contains(&v.as_str()) => error(&format!(
                    "{s}: {var} has placeholder/insecure value '{v}' (run make setup or set a secure value)"
                )),
                Some(_) => {
                    success(&format!("{s}: {var} configured"));
                    continue;
                }
            }
            errors += 1;
        }
    }
    if errors > 0 {
        println!("\n❌ Found {errors} validation errors");
        return false;
    }
    println!("\n✅ All environment variables validated!");
    true
}

/// Problems that block `up`, as printable messages. Empty when all checks pass.
pub fn prerequisite_problems(root: &Path, arg: Option<&str>) -> Vec<String> {
    if !env_path(root, ".").exists() {
        return vec!["❌ Root environment file (.env) not found.\n  Remediation: Run 'make setup' to initialize .env from .env.example.\n".into()];
    }
    let mut problems = Vec::new();
    for s in get_services(arg).iter().filter(|s| *s != ".") {
        let env = env_path(root, s);
        let shown = env.display();
        if !env.exists() {
            problems.push(format!("❌ {s}: Environment file not found ({shown}).\n  Remediation: Run 'make setup' or copy {s}/.env.example to {shown}.\n"));
            continue;
        }
        for var in lookup(VALIDATION_RULES, s).unwrap_or(&[]) {
            let v = read_value(&env, var).unwrap_or_default();
            if v.is_empty() || INVALID_PASSWORD_VALUES.contains(&v.as_str()) {
                problems.push(format!("❌ {s}: Mandatory variable {var} is unset or contains placeholder in {shown}.\n  Remediation: Run 'make setup' to generate credentials or configure {var} in {shown}.\n"));
            }
        }
        for var in lookup(STRONG_PASSWORD_REQUIRED, s).unwrap_or(&[]) {
            let v = read_value(&env, var).unwrap_or_default();
            let weak = Some(v.as_str())
                .filter(|v| !v.is_empty())
                .and_then(validate_password_strength);
            if let Some(problem) = weak {
                problems.push(format!("❌ {s}: {var} in {shown} is too weak. {problem}\n  Remediation: rotate the shared password (see 'Rotate the shared password' in docs/troubleshooting.md).\n"));
            }
        }
    }
    problems
}

/// Print the problems from `prerequisite_problems`. Returns true when all checks pass.
pub fn check_prerequisites(root: &Path, arg: Option<&str>) -> bool {
    let problems = prerequisite_problems(root, arg);
    problems.iter().for_each(|p| println!("{p}"));
    problems.is_empty()
}

fn auth_line(env: &Path) -> String {
    let enabled = read_value(env, "AUTH_ENABLED")
        .unwrap_or_else(|| "false".into())
        .to_lowercase();
    let middleware = read_value(env, "AUTH_MIDDLEWARE").unwrap_or_default();
    let middleware = middleware.trim();
    let effective = if middleware.is_empty() {
        AUTH_GATEWAY_MIDDLEWARE_OFF
    } else {
        middleware
    };
    let state = if AUTH_GATEWAY_MIDDLEWARES_ON.contains(&effective) {
        "on"
    } else {
        "off"
    };
    format!("  AUTH gateway: {state} (AUTH_ENABLED={enabled}, AUTH_MIDDLEWARE={effective})")
}

/// Print the configured info vars for each service that has a `.env`.
pub fn show_summary(root: &Path, arg: Option<&str>) {
    println!(
        "\n╔{}╗\n║ {:^62} ║\n╚{}╝\n",
        "═".repeat(64),
        "Services Configuration",
        "═".repeat(64)
    );
    for s in get_services(arg).iter().filter(|s| *s != ".") {
        let env = env_path(root, s);
        let Ok(text) = fs::read_to_string(&env) else {
            continue;
        };
        println!("Service: {s}");
        match lookup(SERVICE_INFO_VARS, s) {
            None if s == "traefik" => {
                println!("  Routing: HTTP on traefik_proxy (HTTPS via Caddy edge in proxy repo)")
            }
            None => println!("  (configured)"),
            Some(vars) => {
                let lines: Vec<&str> = text
                    .lines()
                    .filter(|l| vars.iter().any(|v| l.starts_with(&format!("{v}="))))
                    .collect();
                if lines.is_empty() {
                    println!("  (no specific ports configured in .env)");
                }
                lines.iter().for_each(|l| println!("  {}", l.trim()));
            }
        }
        if AUTH_OPT_IN_UI_SERVICES.contains(&s.as_str()) {
            println!("{}", auth_line(&env));
        }
        println!();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tree(name: &str, files: &[(&str, &str)]) -> std::path::PathBuf {
        let root = std::env::temp_dir().join(format!("dss-report-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        for (rel, text) in files {
            let path = root.join(rel);
            fs::create_dir_all(path.parent().unwrap()).unwrap();
            fs::write(path, text).unwrap();
        }
        root
    }

    #[test]
    fn weak_zitadel_admin_password_is_refused() {
        let weak = tree(
            "weak",
            &[
                (".env", ""),
                (
                    "zitadel/.env",
                    "ZITADEL_MASTERKEY=abc\nZITADEL_ADMIN_PASSWORD=weakpass\n",
                ),
            ],
        );
        assert!(!check_prerequisites(&weak, Some("zitadel")));
        let strong = tree(
            "strong",
            &[
                (".env", ""),
                (
                    "zitadel/.env",
                    "ZITADEL_MASTERKEY=abc\nZITADEL_ADMIN_PASSWORD=Strong-Password-123\n",
                ),
            ],
        );
        assert!(check_prerequisites(&strong, Some("zitadel")));
    }

    #[test]
    fn legacy_password_value_fails_validation_and_gate() {
        let root = tree(
            "legacy",
            &[
                (".env", ""),
                ("postgres/.env", "POSTGRES16_PASSWORD=Password102!\n"),
            ],
        );
        assert!(!validate_env(&root, Some("postgres")));
        assert!(!check_prerequisites(&root, Some("postgres")));
    }

    #[test]
    fn gate_needs_root_env_and_service_env() {
        let none = tree("none", &[("redis/.env.example", "A=1\n")]);
        assert!(!check_prerequisites(&none, Some("redis")));
        let no_svc = tree("nosvc", &[(".env", "")]);
        assert!(!check_prerequisites(&no_svc, Some("redis")));
    }

    #[test]
    fn auth_line_reports_gateway_state() {
        let root = tree(
            "auth",
            &[(
                "qdrant/.env",
                "AUTH_ENABLED=TRUE\nAUTH_MIDDLEWARE=auth-admin\n",
            )],
        );
        assert!(auth_line(&root.join("qdrant/.env")).contains("AUTH gateway: on"));
        let off = tree("authoff", &[("qdrant/.env", "A=1\n")]);
        assert!(auth_line(&off.join("qdrant/.env"))
            .contains("off (AUTH_ENABLED=false, AUTH_MIDDLEWARE=auth-none)"));
    }
}
