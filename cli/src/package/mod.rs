//! Export a selected service stack into a runnable tree.

pub mod filter;
pub mod templates;
pub mod wizard;
pub mod wizard_ui;

use crate::catalog::{parse_catalog, DEFAULT_DOMAIN};
use crate::config::{PACKAGE_REQUIRES, SERVICES};
use std::fs;
use std::path::{Path, PathBuf};

const MAX_NAME_LENGTH: usize = 48;
const SKIP_DIR_NAMES: &[&str] = &["data", "volumes", "__pycache__", ".venv", "target"];

/// `^[a-z][a-z0-9]*(-[a-z0-9]+)*$`, 1 to 48 characters.
pub fn validate_stack_name(name: &str) -> Result<&str, String> {
    let ok = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit();
    let valid = !name.is_empty()
        && name.len() <= MAX_NAME_LENGTH
        && name.starts_with(|c: char| c.is_ascii_lowercase())
        && name
            .split('-')
            .all(|part| !part.is_empty() && part.chars().all(ok));
    if valid {
        Ok(name)
    } else {
        Err("Stack name must match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ and be 1-48 characters.".into())
    }
}

fn requires_traefik(root: &Path, service: &str) -> bool {
    fs::read_to_string(root.join(service).join("docker-compose.yml"))
        .is_ok_and(|t| t.contains("traefik.enable=true"))
}

/// Transitive `PACKAGE_REQUIRES` plus traefik, in `SERVICES` order.
pub fn resolve_services(selected: &[String], root: &Path) -> Result<Vec<String>, String> {
    let unknown: Vec<&str> = selected
        .iter()
        .map(String::as_str)
        .filter(|s| !SERVICES.contains(s))
        .collect();
    if !unknown.is_empty() {
        return Err(format!("Unknown services: {}", unknown.join(", ")));
    }
    if selected.is_empty() {
        return Err("No services selected.".into());
    }
    let mut chosen: Vec<String> = selected.to_vec();
    loop {
        let mut added: Vec<String> = PACKAGE_REQUIRES
            .iter()
            .filter(|(backend, users)| {
                !chosen.iter().any(|c| c == backend)
                    && users.iter().any(|u| chosen.iter().any(|c| c == u))
            })
            .map(|(backend, _)| backend.to_string())
            .collect();
        if !chosen.iter().any(|c| c == "traefik")
            && chosen.iter().any(|c| requires_traefik(root, c))
        {
            added.push("traefik".into());
        }
        if added.is_empty() {
            break;
        }
        chosen.extend(added);
    }
    Ok(SERVICES
        .iter()
        .filter(|s| chosen.iter().any(|c| c == *s))
        .map(|s| s.to_string())
        .collect())
}

/// `(checked services, dependency services added)`, both in `SERVICES` order.
pub fn partition_selection(
    selected: &[String],
    root: &Path,
) -> Result<(Vec<String>, Vec<String>), String> {
    let resolved = resolve_services(selected, root)?;
    let (checked, added) = resolved.into_iter().partition(|s| selected.contains(s));
    Ok((checked, added))
}

fn skip_dir(name: &str) -> bool {
    SKIP_DIR_NAMES.contains(&name) || name.ends_with("_data")
}

fn skip_file(service: &str, rel: &Path) -> bool {
    let name = rel.file_name().and_then(|n| n.to_str()).unwrap_or("");
    let cert = service == "traefik"
        && rel.parent() == Some(Path::new("certs"))
        && matches!(
            rel.extension().and_then(|e| e.to_str()),
            Some("crt" | "key")
        );
    name == ".env" || cert
}

fn link_escapes(path: &Path, root: &Path) -> bool {
    match (path.canonicalize(), root.canonicalize()) {
        (Ok(target), Ok(root)) => !target.starts_with(root),
        _ => true,
    }
}

/// Copy a service directory, skipping data, secrets, and links that leave the repo.
fn copy_tree(src: &Path, dst: &Path, service: &str, root: &Path, rel: &Path) -> Result<(), String> {
    let io = |e: std::io::Error| format!("{}: {e}", src.display());
    fs::create_dir_all(dst).map_err(io)?;
    for entry in fs::read_dir(src).map_err(io)? {
        let entry = entry.map_err(io)?;
        let (path, name) = (entry.path(), entry.file_name());
        let rel = rel.join(&name);
        let kind = entry.file_type().map_err(io)?;
        if kind.is_symlink() {
            if !link_escapes(&path, root) {
                #[cfg(unix)]
                std::os::unix::fs::symlink(fs::read_link(&path).map_err(io)?, dst.join(&name))
                    .map_err(io)?;
            }
        } else if kind.is_dir() {
            if !skip_dir(&name.to_string_lossy()) {
                copy_tree(&path, &dst.join(&name), service, root, &rel)?;
            }
        } else if !skip_file(service, &rel) {
            fs::copy(&path, dst.join(&name)).map_err(io)?;
        }
    }
    Ok(())
}

fn write(path: &Path, text: &str) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    fs::write(path, text).map_err(|e| format!("{}: {e}", path.display()))
}

fn copy_binary(root: &Path, dest: &Path) -> Result<(), String> {
    let release = root.join("cli/target/release/dss");
    let src = if release.is_file() {
        release
    } else {
        std::env::current_exe().map_err(|e| e.to_string())?
    };
    let target = dest.join("dss");
    fs::copy(&src, &target).map_err(|e| format!("{}: {e}", target.display()))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let mut perms = fs::metadata(&target)
            .map_err(|e| e.to_string())?
            .permissions();
        perms.set_mode(0o755);
        fs::set_permissions(&target, perms).map_err(|e| e.to_string())?;
    }
    Ok(())
}

fn build(services: &[String], name: &str, root: &Path, dest: &Path) -> Result<(), String> {
    for service in services {
        let source = root.join(service);
        if !source.is_dir() {
            return Err(format!("Service directory not found: {}", source.display()));
        }
        copy_tree(&source, &dest.join(service), service, root, Path::new(""))?;
    }
    fs::copy(
        root.join("docker-compose.shared.yml"),
        dest.join("docker-compose.shared.yml"),
    )
    .map_err(|e| e.to_string())?;
    let example = fs::read_to_string(root.join(".env.example")).map_err(|e| e.to_string())?;
    write(
        &dest.join(".env.example"),
        &filter::filter_env_example(&example, services),
    )?;
    copy_binary(root, dest)?;
    write(
        &dest.join(crate::config::MANIFEST_FILE),
        &filter::manifest(services)?,
    )?;
    write(
        &dest.join("Makefile"),
        &templates::render_makefile(services),
    )?;
    let raw =
        fs::read_to_string(root.join("cli/service_catalog.json")).map_err(|e| e.to_string())?;
    let shown = parse_catalog(&raw, DEFAULT_DOMAIN)?;
    write(
        &dest.join("README.md"),
        &templates::render_readme(name, services, &shown),
    )?;
    write(&dest.join(".gitignore"), templates::PACKAGE_GITIGNORE)
}

/// Write a runnable tree for `selected` services. Refuses an existing destination.
pub fn export_stack(
    selected: &[String],
    name: &str,
    root: &Path,
    destination: Option<PathBuf>,
) -> Result<PathBuf, String> {
    validate_stack_name(name)?;
    let root = root
        .canonicalize()
        .map_err(|e| format!("{}: {e}", root.display()))?;
    let services = resolve_services(selected, &root)?;
    let dest = destination.unwrap_or_else(|| root.join("dist").join(name));
    if dest.exists() {
        return Err(format!("{} already exists", dest.display()));
    }
    fs::create_dir_all(&dest).map_err(|e| e.to_string())?;
    let dest = dest.canonicalize().map_err(|e| e.to_string())?;
    if let Err(message) = build(&services, name, &root, &dest) {
        let _ = fs::remove_dir_all(&dest);
        return Err(message);
    }
    Ok(dest)
}

#[cfg(test)]
#[path = "export_tests.rs"]
mod tests;
