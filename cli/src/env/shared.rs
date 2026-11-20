//! Fill unique secrets and apply the one shared password to every `.env`.

use super::secrets::{bcrypt_auth, generate_hs256_jwt, generate_password, generate_secret};
use super::tables::*;
use super::{env_path, error, get_services, read_value, set_value, success, warning};
use crate::config::{
    validate_password_strength, INVALID_PASSWORD_VALUES, LEGACY_PLACEHOLDER_PASSWORD,
};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

const LEGACY_DASHBOARD_HASH: &str = "admin:$apr1$dsslocal$d6fWuAuh2eC9xV6eu7kMP.";

fn jwt_role(var: &str) -> &'static str {
    if var == "ANON_KEY" {
        "anon"
    } else {
        "service_role"
    }
}

/// Double each lone `$` so Docker Compose does not expand it.
pub fn escape_dollars(value: &str) -> String {
    let chars: Vec<char> = value.chars().collect();
    let mut out = String::new();
    for (i, c) in chars.iter().enumerate() {
        let lone = *c == '$' && (i == 0 || chars[i - 1] != '$') && chars.get(i + 1) != Some(&'$');
        out.push(*c);
        if lone {
            out.push('$');
        }
    }
    out
}

fn generate_value(
    root: &Path,
    env: &Path,
    var: &str,
    m: Method,
    n: usize,
) -> Result<String, String> {
    match m {
        Method::Htpasswd => {
            let shared =
                read_value(&env_path(root, "."), "DSS_SHARED_PASSWORD").unwrap_or_default();
            if shared.is_empty() || INVALID_PASSWORD_VALUES.contains(&shared.as_str()) {
                return Err("Set a secure DSS_SHARED_PASSWORD first (run make setup).".into());
            }
            generate_secret(m, n, &shared)
        }
        Method::JwtHs256 => {
            let secret = read_value(env, "JWT_SECRET")
                .filter(|s| !s.is_empty())
                .ok_or_else(|| {
                    format!("{}: set JWT_SECRET before generating {var}.", env.display())
                })?;
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map_or(0, |d| d.as_secs());
            Ok(generate_hs256_jwt(&secret, jwt_role(var), now))
        }
        _ => generate_secret(m, n, ""),
    }
}

fn fill_one(
    root: &Path,
    s: &str,
    env: &Path,
    var: &str,
    m: Method,
    n: usize,
) -> Result<bool, String> {
    let current = read_value(env, var).unwrap_or_default();
    let is_dash = var == "TRAEFIK_DASHBOARD_AUTH";
    if is_dash
        && !current.is_empty()
        && current != LEGACY_DASHBOARD_HASH
        && current != LEGACY_DASHBOARD_HASH.replace('$', "$$")
    {
        let escaped = escape_dollars(&current);
        if escaped != current {
            set_value(env, var, &escaped).map_err(|e| e.to_string())?;
            success(&format!("{s}: escaped {var} for Docker Compose"));
        } else {
            success(&format!("{s}: {var} already set (left unchanged)"));
        }
        return Ok(false);
    }
    if !current.is_empty() && !is_dash {
        if KNOWN_SECRET_PLACEHOLDERS.contains(&current.as_str()) {
            warning(&format!(
                "{s}: {var} still holds a public placeholder (left unchanged)"
            ));
        } else {
            success(&format!("{s}: {var} already set (left unchanged)"));
        }
        return Ok(false);
    }
    let value = generate_value(root, env, var, m, n)?;
    set_value(env, var, &value).map_err(|e| e.to_string())?;
    success(&format!("{s}: generated {var}"));
    Ok(true)
}

/// Fill empty auto-generated secrets. Returns how many values were written.
pub fn fill_secrets(root: &Path, arg: Option<&str>) -> Result<usize, String> {
    println!("\nFilling empty auto-generated secrets...\n");
    let mut filled = 0;
    for s in get_services(arg) {
        let env = env_path(root, &s);
        let Some(specs) = lookup(AUTO_SECRETS, &s) else {
            continue;
        };
        if !env.exists() {
            continue;
        }
        for (var, method, nbytes) in specs {
            filled += usize::from(fill_one(root, &s, &env, var, *method, *nbytes)?);
        }
    }
    if filled == 0 {
        println!("✅ No empty auto-generated secrets to fill.");
    } else {
        println!("\n✅ Generated {filled} secret value(s).");
    }
    sync_garage_ui_token(root);
    Ok(filled)
}

fn sync_garage_ui_token(root: &Path) {
    let (ui, garage) = (env_path(root, "garage_ui"), env_path(root, "garage"));
    if !ui.exists() || !garage.exists() {
        return;
    }
    let token = read_value(&garage, "GARAGE_ADMIN_TOKEN").unwrap_or_default();
    if token.is_empty()
        || !read_value(&ui, "GARAGE_ADMIN_TOKEN")
            .unwrap_or_default()
            .is_empty()
    {
        return;
    }
    if set_value(&ui, "GARAGE_ADMIN_TOKEN", &token).is_ok() {
        success("garage_ui: copied GARAGE_ADMIN_TOKEN from garage/.env");
    }
}

fn require_strong(password: &str, source: &str) -> Result<String, String> {
    match validate_password_strength(password) {
        Some(problem) => Err(format!("{source}: {problem}")),
        None => Ok(password.to_string()),
    }
}

/// Pick the shared password: explicit, `DSS_SHARED_PASSWORD` env, root `.env`, or random.
pub fn resolve_password(
    root: &Path,
    explicit: Option<&str>,
    from_env: Option<&str>,
) -> Result<String, String> {
    if let Some(p) = explicit.filter(|p| !p.is_empty()) {
        return require_strong(p, "--password");
    }
    if let Some(p) = from_env.map(str::trim).filter(|p| !p.is_empty()) {
        return require_strong(p, "DSS_SHARED_PASSWORD env");
    }
    let existing = read_value(&env_path(root, "."), "DSS_SHARED_PASSWORD").unwrap_or_default();
    if !existing.is_empty() && !INVALID_PASSWORD_VALUES.contains(&existing.as_str()) {
        // Data services already store this password in their volumes: never rotate it implicitly.
        if let Some(problem) = validate_password_strength(&existing) {
            warning(&format!("root .env DSS_SHARED_PASSWORD: {problem}"));
            println!("  Kept as-is. To rotate it, see 'Rotate the shared password' in docs/troubleshooting.md.\n");
        }
        return Ok(existing);
    }
    Ok(generate_password(32))
}

fn should_overwrite(key: &str, current: Option<&str>, force: bool) -> bool {
    if key == "GARAGE_UI_AUTH_USER_PASS"
        && current.is_some_and(|c| c.contains(GARAGE_UI_AUTH_PLACEHOLDER))
    {
        return true;
    }
    match current {
        _ if force => true,
        None => true,
        Some(c) => {
            SHARED_PASSWORD_PLACEHOLDERS.contains(&c) || c.contains(LEGACY_PLACEHOLDER_PASSWORD)
        }
    }
}

/// `(service, key, value)` for every shared-password key whose `.env` exists.
fn targets(root: &Path, password: &str) -> Result<Vec<(String, String, String)>, String> {
    let has = |s: &str| env_path(root, s).exists();
    let mut out = Vec::new();
    for (s, keys) in SHARED_PASSWORD_KEYS.iter().filter(|(s, _)| has(s)) {
        out.extend(
            keys.iter()
                .map(|k| (s.to_string(), k.to_string(), password.to_string())),
        );
    }
    for (s, k, tpl) in SHARED_PASSWORD_TEMPLATES.iter().filter(|(s, _, _)| has(s)) {
        out.push((
            s.to_string(),
            k.to_string(),
            tpl.replace("{password}", password),
        ));
    }
    for (s, k, user) in SHARED_PASSWORD_BCRYPT.iter().filter(|(s, _, _)| has(s)) {
        out.push((s.to_string(), k.to_string(), bcrypt_auth(user, password)?));
    }
    Ok(out)
}

/// Apply ONE shared password to every listed key. Returns the password.
pub fn fill_shared_password(
    root: &Path,
    password: Option<&str>,
    force: bool,
    dry_run: bool,
) -> Result<String, String> {
    let from_env = std::env::var("DSS_SHARED_PASSWORD").ok();
    let resolved = resolve_password(root, password, from_env.as_deref())?;
    if INVALID_PASSWORD_VALUES.contains(&resolved.as_str()) {
        let msg = format!(
            "{LEGACY_PLACEHOLDER_PASSWORD} is an insecure placeholder; choose a secure password."
        );
        error(&msg);
        return Err(msg);
    }
    println!("\nApplying shared password across services...\n");
    let root_env = env_path(root, ".");
    if !dry_run && !root_env.exists() && root.join(".env.example").exists() {
        fs::copy(root.join(".env.example"), &root_env).map_err(|e| e.to_string())?;
        success("Created ./.env from .env.example");
    }
    let (mut updated, mut skipped) = (0, 0);
    for (s, key, value) in targets(root, &resolved)? {
        let path = env_path(root, &s);
        if !should_overwrite(&key, read_value(&path, &key).as_deref(), force) {
            skipped += 1;
            continue;
        }
        if dry_run {
            println!("  would set {}: {key}", path.display());
        } else {
            set_value(&path, &key, &value).map_err(|e| e.to_string())?;
            success(&format!("{}: {key}", path.display()));
        }
        updated += 1;
    }
    println!("\n✅ Shared password sync complete (updated={updated}, skipped_custom={skipped}).");
    Ok(resolved)
}

#[cfg(test)]
#[path = "shared_tests.rs"]
mod tests;
