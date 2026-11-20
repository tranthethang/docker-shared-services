//! Service catalog embedded from `service_catalog.json`.

use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::path::Path;

use crate::stack::read_env_value;

const CATALOG_JSON: &str = include_str!("../service_catalog.json");
const DOMAIN_PLACEHOLDER: &str = "{domain}";
pub const DEFAULT_DOMAIN: &str = "sandbox.localhost";

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Entry {
    pub category: String,
    pub description: String,
    pub containers: Vec<String>,
    pub web_ui: Vec<String>,
    pub info: Vec<String>,
}

pub type Catalog = BTreeMap<String, Entry>;

/// `DOMAIN` from an env file; `sandbox.localhost` when missing or empty.
pub fn root_domain(env_path: &Path) -> String {
    read_env_value(env_path, "DOMAIN")
        .filter(|v| !v.is_empty())
        .unwrap_or_else(|| DEFAULT_DOMAIN.to_string())
}

fn fill(items: &mut [String], domain: &str) {
    for item in items {
        *item = item.replace(DOMAIN_PLACEHOLDER, domain);
    }
}

/// Parse catalog JSON and substitute `{domain}` in `web_ui` and `info`.
pub fn parse_catalog(json: &str, domain: &str) -> Result<Catalog, String> {
    let mut catalog: Catalog = serde_json::from_str(json).map_err(|e| e.to_string())?;
    for entry in catalog.values_mut() {
        fill(&mut entry.web_ui, domain);
        fill(&mut entry.info, domain);
    }
    Ok(catalog)
}

/// The embedded catalog with `DOMAIN` taken from the root `.env`.
pub fn load_catalog() -> Catalog {
    let domain = root_domain(Path::new(crate::stack::ROOT_ENV_FILE));
    parse_catalog(CATALOG_JSON, &domain).expect("embedded service_catalog.json is valid")
}

pub const CATEGORIES: &[&str] = &[
    "Database",
    "Cache & Queue",
    "Storage",
    "Auth & Gateway",
    "CI/CD",
    "Workflow & Automation",
    "Observability",
    "Admin UI",
    "AI & Search",
    "Dev Tools",
];

/// Drift between the catalog, `SERVICES`, and compose service names.
pub fn catalog_problems(catalog: &Catalog, compose: &BTreeMap<String, Vec<String>>) -> Vec<String> {
    use crate::config::{active_services, SERVICES};
    let mut problems = Vec::new();
    for name in active_services() {
        let Some(entry) = catalog.get(*name) else {
            problems.push(format!("{name}: missing from service_catalog.json"));
            continue;
        };
        if !CATEGORIES.contains(&entry.category.as_str()) {
            problems.push(format!(
                "{name}: category {:?} is not one of {CATEGORIES:?}",
                entry.category
            ));
        }
        if entry.description.trim().is_empty() {
            problems.push(format!("{name}: description must be a non-empty string"));
        }
        if let Some(services) = compose.get(*name) {
            let (mut a, mut b) = (entry.containers.clone(), services.clone());
            a.sort();
            b.sort();
            if a != b {
                problems.push(format!(
                    "{name}: containers {a:?} != compose services {b:?}"
                ));
            }
        }
        for url in entry.web_ui.iter().filter(|u| !u.starts_with("https://")) {
            problems.push(format!(
                "{name}: web_ui URL {url:?} must start with https://"
            ));
        }
    }
    for name in catalog.keys().filter(|n| !SERVICES.contains(&n.as_str())) {
        problems.push(format!(
            "{name}: in service_catalog.json but not in SERVICES"
        ));
    }
    problems
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::SERVICES;

    #[test]
    fn embedded_catalog_matches_services() {
        let catalog = parse_catalog(CATALOG_JSON, DEFAULT_DOMAIN).unwrap();
        for name in SERVICES {
            assert!(catalog.contains_key(*name), "{name} missing from catalog");
        }
        assert_eq!(catalog.len(), SERVICES.len());
    }

    #[test]
    fn substitutes_domain_in_urls_and_info() {
        let catalog = parse_catalog(CATALOG_JSON, "example.test").unwrap();
        let adminer = &catalog["adminer"];
        assert_eq!(adminer.web_ui, ["https://adminer.example.test"]);
        assert!(adminer.info[0].contains("example.test"));
        assert!(!adminer.info[0].contains("{domain}"));
    }

    #[test]
    fn web_ui_urls_are_https() {
        let catalog = parse_catalog(CATALOG_JSON, DEFAULT_DOMAIN).unwrap();
        for (name, entry) in &catalog {
            assert!(
                entry.web_ui.iter().all(|u| u.starts_with("https://")),
                "{name}"
            );
        }
    }

    #[test]
    fn missing_domain_falls_back_to_default() {
        assert_eq!(root_domain(Path::new("/nonexistent/.env")), DEFAULT_DOMAIN);
    }

    #[test]
    fn catalog_problems_flags_drift() {
        let mut catalog = parse_catalog(CATALOG_JSON, DEFAULT_DOMAIN).unwrap();
        assert!(catalog_problems(&catalog, &BTreeMap::new()).is_empty());
        let wrong = BTreeMap::from([("redis".to_string(), vec!["other".to_string()])]);
        assert!(catalog_problems(&catalog, &wrong)[0].starts_with("redis: containers"));
        catalog.remove("redis");
        catalog.get_mut("adminer").unwrap().category = "Nope".into();
        let problems = catalog_problems(&catalog, &BTreeMap::new());
        assert!(problems.iter().any(|p| p.contains("redis: missing")));
        assert!(problems.iter().any(|p| p.contains("adminer: category")));
    }
}
