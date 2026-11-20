//! Destructive subcommands: teardown, prune, and `.env` removal. Each one confirms first.

use crate::commands::{confirm, inherit, Res};
use crate::config::active_services;
use crate::docker::compose::{compose_with, sort_for_shutdown};
use std::path::{Path, PathBuf};

/// `docker compose down -v` for each service, in shutdown order.
pub fn teardown(force: bool) -> Res {
    println!("⚠️  WARNING: This will remove all data from all services!");
    if !confirm("Are you sure?", force) {
        println!("Operation cancelled");
        return Ok(());
    }
    let names: Vec<String> = active_services()
        .iter()
        .filter(|s| Path::new(s).join("docker-compose.yml").is_file())
        .map(|s| s.to_string())
        .collect();
    let mut failed = Vec::new();
    for service in sort_for_shutdown(&names) {
        println!("ℹ️  Removing {service}...");
        if !inherit(&compose_with(&service, &["down", "-v"])?) {
            failed.push(service);
        }
    }
    if !failed.is_empty() {
        return Err(format!("Remove failed for: {}", failed.join(", ")));
    }
    println!("✅ All containers and volumes removed");
    Ok(())
}

pub fn prune(force: bool) -> Res {
    if !confirm("Remove unused Docker resources, including volumes?", force) {
        println!("Operation cancelled");
        return Ok(());
    }
    println!("Pruning Docker resources...");
    if !inherit(&[
        "system".into(),
        "prune".into(),
        "-f".into(),
        "--volumes".into(),
    ]) {
        return Err("docker system prune failed".into());
    }
    println!("✅ Pruned");
    Ok(())
}

/// `.env` files next to a `.env.example` in `dir` and its immediate subdirectories.
pub fn removable_env_files(dir: &Path) -> Vec<PathBuf> {
    let mut found = Vec::new();
    let mut dirs = vec![dir.to_path_buf()];
    if let Ok(entries) = std::fs::read_dir(dir) {
        dirs.extend(entries.flatten().map(|e| e.path()).filter(|p| p.is_dir()));
    }
    for d in dirs {
        if d.join(".env.example").is_file() && d.join(".env").is_file() {
            found.push(d.join(".env"));
        }
    }
    found.sort();
    found
}

pub fn remove_config(force: bool) -> Res {
    println!("Searching for .env files with a matching .env.example...");
    let files = removable_env_files(Path::new("."));
    if files.is_empty() {
        println!("No .env files found.");
        return Ok(());
    }
    println!("\nFound {} .env file(s):", files.len());
    files.iter().for_each(|f| println!("  {}", f.display()));
    if !confirm("\nRemove these .env files?", force) {
        println!("Operation cancelled");
        return Ok(());
    }
    for f in &files {
        std::fs::remove_file(f).map_err(|e| format!("{}: {e}", f.display()))?;
        println!("  Removed {}", f.display());
    }
    println!(
        "\n✅ Removed {} .env file(s). Run 'dss setup' to recreate from .env.example.",
        files.len()
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_env_files_with_a_matching_example() {
        let dir = std::env::temp_dir().join(format!("dss-rmcfg-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        for (sub, files) in [
            ("a", vec![".env", ".env.example"]),
            ("b", vec![".env"]),
            ("c", vec![".env.example"]),
        ] {
            std::fs::create_dir_all(dir.join(sub)).unwrap();
            for f in files {
                std::fs::write(dir.join(sub).join(f), "").unwrap();
            }
        }
        assert_eq!(removable_env_files(&dir), [dir.join("a/.env")]);
    }
}
