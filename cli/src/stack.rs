//! Stack identity: `SANDBOX_NAME` prefix and shared network names and subnets.
//!
//! An empty `SANDBOX_NAME` keeps every historic name. A named stack gets its own
//! Compose projects, networks, and subnets so several checkouts can share one host.

use std::path::Path;

pub const ROOT_ENV_FILE: &str = ".env";
pub const NETWORK_BASES: [&str; 3] = ["traefik_proxy", "backend_net", "data_net"];
const MAX_SUBNET_BASE: u32 = 253;

/// Raw value for `key` in an env file, quotes stripped. `None` when missing.
pub fn read_env_value(path: &Path, key: &str) -> Option<String> {
    let text = std::fs::read_to_string(path).ok()?;
    text.lines().find_map(|line| {
        let (name, value) = line.split_once('=')?;
        (name == key).then(|| {
            value
                .trim()
                .trim_matches(|c| c == '\'' || c == '"')
                .to_string()
        })
    })
}

fn root_value(key: &str) -> String {
    read_env_value(Path::new(ROOT_ENV_FILE), key).unwrap_or_default()
}

fn valid_name(name: &str) -> bool {
    let mut chars = name.chars();
    let ok = |c: char| c.is_ascii_lowercase() || c.is_ascii_digit();
    chars.next().is_some_and(ok) && chars.all(|c| ok(c) || c == '_' || c == '-')
}

fn check_name(name: String) -> Result<String, String> {
    if !name.is_empty() && !valid_name(&name) {
        return Err(format!(
            "SANDBOX_NAME={name:?} is invalid; use lowercase letters, digits, '_' or '-'"
        ));
    }
    Ok(name)
}

fn check_base(raw: &str) -> Result<u32, String> {
    let raw = if raw.is_empty() { "0" } else { raw };
    let base: u32 = raw
        .parse()
        .map_err(|_| format!("SANDBOX_SUBNET_BASE={raw:?} is invalid; use an integer"))?;
    if base > MAX_SUBNET_BASE {
        return Err(format!(
            "SANDBOX_SUBNET_BASE={base} is invalid; use 0 to {MAX_SUBNET_BASE}"
        ));
    }
    Ok(base)
}

/// The validated `SANDBOX_NAME`, or an empty string for the unnamed stack.
pub fn stack_name() -> Result<String, String> {
    check_name(root_value("SANDBOX_NAME"))
}

/// The validated `SANDBOX_SUBNET_BASE` (default 0).
pub fn subnet_base() -> Result<u32, String> {
    check_base(&root_value("SANDBOX_SUBNET_BASE"))
}

fn prefixed(name: &str, sep: char, base: &str) -> String {
    if name.is_empty() {
        base.to_string()
    } else {
        format!("{name}{sep}{base}")
    }
}

/// Compose project for a service: `<SANDBOX_NAME>-<service>` or the bare name.
pub fn project_name(service: &str) -> Result<String, String> {
    Ok(prefixed(&stack_name()?, '-', service))
}

fn pairs_for(name: &str, first: u32) -> Vec<String> {
    NETWORK_BASES
        .iter()
        .zip(first..)
        .map(|(base, octet)| format!("{}:10.{octet}.0.0/16", prefixed(name, '_', base)))
        .collect()
}

/// `name:subnet` for each shared network, adjacent /16s in 10/8 from the base.
pub fn network_pairs() -> Result<Vec<String>, String> {
    Ok(pairs_for(&stack_name()?, subnet_base()?))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unnamed_stack_keeps_historic_names() {
        assert_eq!(
            pairs_for("", 0),
            [
                "traefik_proxy:10.0.0.0/16",
                "backend_net:10.1.0.0/16",
                "data_net:10.2.0.0/16"
            ]
        );
    }

    #[test]
    fn named_stack_prefixes_networks_and_shifts_subnets() {
        assert_eq!(pairs_for("dev", 10)[2], "dev_data_net:10.12.0.0/16");
        assert_eq!(prefixed("dev", '-', "redis"), "dev-redis");
    }

    #[test]
    fn rejects_bad_names_and_bases() {
        assert!(check_name("Bad Name".into()).is_err());
        assert!(check_name("-lead".into()).is_err());
        assert_eq!(check_name("ok_name-1".into()).unwrap(), "ok_name-1");
        assert_eq!(check_base("").unwrap(), 0);
        assert!(check_base("abc").is_err());
        assert!(check_base("254").is_err());
        assert_eq!(check_base("253").unwrap(), 253);
    }
}
