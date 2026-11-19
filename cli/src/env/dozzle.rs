//! Generate `dozzle/data/users.yml` from the shared password.

use crate::config::LEGACY_PLACEHOLDER_PASSWORD;
use std::fs;
use std::path::Path;
use std::process::Command;

use super::read_value;

/// Pick the Dozzle password: env value first, then the root `.env`.
pub fn dozzle_password(env_value: Option<&str>, root_env: &Path) -> Result<String, String> {
    let password = env_value
        .filter(|p| !p.is_empty())
        .map(String::from)
        .or_else(|| read_value(root_env, "DSS_SHARED_PASSWORD"))
        .unwrap_or_default();
    if password.is_empty() || password == LEGACY_PLACEHOLDER_PASSWORD {
        return Err(format!(
            "DSS_SHARED_PASSWORD is missing or still {LEGACY_PLACEHOLDER_PASSWORD}. Run make setup before generating Dozzle users."
        ));
    }
    Ok(password)
}

/// Write an admin entry to `users_file` unless it exists. A directory there is replaced.
pub fn ensure_dozzle_users(users_file: &Path, root_env: &Path) -> Result<(), String> {
    let io = |e: std::io::Error| e.to_string();
    if let Some(parent) = users_file.parent() {
        fs::create_dir_all(parent).map_err(io)?;
    }
    if users_file.is_dir() {
        println!(
            "  {} is a directory -> removing and regenerating...",
            users_file.display()
        );
        fs::remove_dir_all(users_file).map_err(io)?;
    }
    if users_file.is_file() {
        println!("  {} already exists", users_file.display());
        return Ok(());
    }
    let env_value = std::env::var("DSS_SHARED_PASSWORD").ok();
    let password = dozzle_password(env_value.as_deref(), root_env)?;
    println!(
        "  {} not found -> generating admin (shared password)...",
        users_file.display()
    );
    let out = Command::new("docker")
        .args([
            "run",
            "--rm",
            "-i",
            "amir20/dozzle",
            "generate",
            "admin",
            "--password",
        ])
        .arg(&password)
        .args(["--email", "admin@example.com", "--name", "Admin"])
        .output()
        .map_err(io)?;
    if !out.status.success() {
        return Err(format!(
            "docker run dozzle failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    fs::write(users_file, out.stdout).map_err(io)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_missing_and_legacy_password() {
        let nowhere = Path::new("/nonexistent/.env");
        assert!(dozzle_password(None, nowhere).is_err());
        assert!(dozzle_password(Some("Password102!"), nowhere).is_err());
        assert_eq!(
            dozzle_password(Some("Good-Pass-1234567"), nowhere).unwrap(),
            "Good-Pass-1234567"
        );
    }
}
