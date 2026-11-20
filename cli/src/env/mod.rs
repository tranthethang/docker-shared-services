//! `.env` file helpers: read, set, check, create, and merge from `.env.example`.

pub mod dozzle;
pub mod report;
pub mod secrets;
pub mod shared;
pub mod tables;

use crate::config::active_services;
use std::fs;
use std::path::{Path, PathBuf};

pub fn success(msg: &str) {
    println!("✅ {msg}");
}
pub fn warning(msg: &str) {
    println!("⚠️  {msg}");
}
pub fn error(msg: &str) {
    println!("❌ {msg}");
}

/// `(KEY, raw value)` for each assignment line. Comments and blank lines are skipped.
pub fn assignments(text: &str) -> Vec<(String, String)> {
    text.lines()
        .filter_map(|line| {
            let (key, value) = line.split_once('=')?;
            let mut chars = key.chars();
            let head = chars
                .next()
                .is_some_and(|c| c.is_ascii_alphabetic() || c == '_');
            let tail = chars.all(|c| c.is_ascii_alphanumeric() || c == '_');
            (head && tail).then(|| (key.to_string(), value.to_string()))
        })
        .collect()
}

/// Value for `key` with quotes stripped. `None` when the key or file is missing.
pub fn read_value(path: &Path, key: &str) -> Option<String> {
    let text = fs::read_to_string(path).ok()?;
    assignments(&text)
        .into_iter()
        .find(|(name, _)| name == key)
        .map(|(_, v)| v.trim().trim_matches(|c| c == '\'' || c == '"').to_string())
}

/// Replace `KEY=...` in place, or append it when absent.
pub fn set_value(path: &Path, key: &str, value: &str) -> std::io::Result<()> {
    let text = fs::read_to_string(path)?;
    let prefix = format!("{key}=");
    let mut replaced = false;
    let mut out = String::new();
    for line in text.lines() {
        let is_key = assignments(line).first().is_some_and(|(k, _)| k == key);
        if is_key && !replaced {
            out.push_str(&format!("{prefix}{value}\n"));
            replaced = true;
        } else if !is_key {
            out.push_str(line);
            out.push('\n');
        }
    }
    if !replaced {
        out.push_str(&format!("{prefix}{value}\n"));
    }
    fs::write(path, out)
}

/// Env file for a service dir. `.` is the repo root.
pub fn env_path(root: &Path, service: &str) -> PathBuf {
    root.join(service).join(".env")
}

fn example_path(root: &Path, service: &str) -> PathBuf {
    root.join(service).join(".env.example")
}

/// `.` plus every service for `all`; a single known service otherwise.
pub fn get_services(arg: Option<&str>) -> Vec<String> {
    match arg {
        None | Some("all") => std::iter::once(".")
            .chain(active_services().iter().copied())
            .map(String::from)
            .collect(),
        Some(s) if s == "." || active_services().contains(&s) => vec![s.to_string()],
        Some(_) => Vec::new(),
    }
}

/// Print the state of each `.env`. Returns true when some are missing.
pub fn check_env(root: &Path, arg: Option<&str>) -> bool {
    println!("Checking .env files...\n");
    let mut missing = 0;
    for s in get_services(arg) {
        if env_path(root, &s).exists() {
            success(&format!("{s}/.env exists"));
        } else if example_path(root, &s).exists() {
            warning(&format!("{s}/.env missing (only .env.example exists)"));
            missing += 1;
        } else {
            error(&format!("{s}/.env.example not found"));
        }
    }
    if missing > 0 {
        println!("\nFound {missing} services missing .env files");
    }
    missing > 0
}

/// Copy `.env.example` to `.env` where `.env` is missing. Returns the created dirs.
pub fn create_env(root: &Path, arg: Option<&str>) -> Vec<String> {
    println!("\nCreating .env files from .env.example...\n");
    let mut created = Vec::new();
    for s in get_services(arg) {
        let (src, dst) = (example_path(root, &s), env_path(root, &s));
        if src.exists() && !dst.exists() && fs::copy(&src, &dst).is_ok() {
            success(&format!("Created {s}/.env"));
            created.push(s);
        }
    }
    if created.is_empty() {
        println!("\n✅ No missing .env files to create.");
    } else {
        println!("\n✅ .env files created successfully!");
    }
    warning("Next: shared password sync (passwords) + unique secrets (fill-secrets).");
    created
}

/// Keys in `example` (first occurrence wins) that `current` does not define.
pub fn missing_keys(example: &str, current: &str) -> Vec<(String, String)> {
    let have: Vec<String> = assignments(current).into_iter().map(|(k, _)| k).collect();
    let mut seen: Vec<String> = Vec::new();
    let mut out = Vec::new();
    for (key, value) in assignments(example) {
        if seen.contains(&key) {
            continue;
        }
        seen.push(key.clone());
        if !have.contains(&key) {
            out.push((key, value));
        }
    }
    out
}

/// Append keys from `.env.example` that `.env` lacks. Never overwrites a value.
pub fn merge_missing(root: &Path, arg: Option<&str>) -> usize {
    println!("\nMerging missing keys from .env.example into existing .env files...\n");
    let mut added = 0;
    for s in get_services(arg) {
        let (Ok(example), Ok(mut content)) = (
            fs::read_to_string(example_path(root, &s)),
            fs::read_to_string(env_path(root, &s)),
        ) else {
            continue;
        };
        let missing = missing_keys(&example, &content);
        if missing.is_empty() {
            continue;
        }
        if !content.is_empty() && !content.ends_with('\n') {
            content.push('\n');
        }
        if !content.trim().is_empty() {
            content.push('\n');
        }
        for (key, value) in &missing {
            content.push_str(&format!("{key}={value}\n"));
            success(&format!("{s}: added {key}"));
            added += 1;
        }
        let _ = fs::write(env_path(root, &s), content);
    }
    if added == 0 {
        println!("✅ No missing keys to merge.");
    } else {
        println!("\n✅ Added {added} missing key(s) from .env.example.");
    }
    added
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("dss-env-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    #[test]
    fn read_and_set_values() {
        let file = tmp("set").join(".env");
        fs::write(&file, "# c\nA='one'\nB=2").unwrap();
        assert_eq!(read_value(&file, "A").as_deref(), Some("one"));
        set_value(&file, "B", "3").unwrap();
        set_value(&file, "C", "4").unwrap();
        assert_eq!(
            fs::read_to_string(&file).unwrap(),
            "# c\nA='one'\nB=3\nC=4\n"
        );
        assert_eq!(read_value(&file, "MISSING"), None);
    }

    #[test]
    fn merge_keeps_existing_values_and_adds_missing_keys() {
        let example = "A=new\nB=two\nB=dup\n# note\nC=\n";
        let current = "A=mine\nC=custom";
        assert_eq!(
            missing_keys(example, current),
            [("B".to_string(), "two".to_string())]
        );
        assert!(
            missing_keys("A=x\n", "A=\n").is_empty(),
            "empty values count as set"
        );
    }

    #[test]
    fn merge_missing_appends_to_files_on_disk() {
        let dir = tmp("merge");
        let svc = dir.join("redis");
        fs::create_dir_all(&svc).unwrap();
        fs::write(svc.join(".env.example"), "A=1\nB=2\n").unwrap();
        fs::write(svc.join(".env"), "A=keep").unwrap();
        let added = merge_missing(&dir, Some("redis"));
        assert_eq!(added, 1);
        assert_eq!(
            fs::read_to_string(svc.join(".env")).unwrap(),
            "A=keep\n\nB=2\n"
        );
    }

    #[test]
    fn get_services_resolves_args() {
        assert_eq!(get_services(Some("redis")), ["redis"]);
        assert_eq!(get_services(Some(".")), ["."]);
        assert!(get_services(Some("nope")).is_empty());
        assert_eq!(get_services(None)[0], ".");
    }
}
