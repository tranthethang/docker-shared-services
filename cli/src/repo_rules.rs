//! Repo-wide checks that read the Compose files and sources. They run under `cargo test`.
//!
//! Compose files share one 2-space layout, so a line reader is enough and no YAML crate is needed.

use crate::config::{PACKAGE_REQUIRES, SERVICES};
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

const PREFIX: &str = "${SANDBOX_NAME:+${SANDBOX_NAME}-}";
const RESOURCE_PREFIX: &str = "${SANDBOX_NAME:+${SANDBOX_NAME}_}";
const STACK_LABEL: &str = "\"sandbox.stack=${SANDBOX_NAME:-sandbox}\"";
/// Compose service names that hold data, keyed by service directory.
const DATA_STORES: &[(&str, &[&str])] = &[
    ("chromadb", &["chromadb"]),
    ("kafka", &["kafka"]),
    ("mariadb", &["mariadb"]),
    ("memcached", &["memcached"]),
    ("mongodb", &["mongodb"]),
    ("mysql8", &["mysql8"]),
    ("otel", &["loki"]),
    ("pgvector", &["pgvector"]),
    ("postgres", &["postgres"]),
    ("qdrant", &["qdrant"]),
    ("rabbitmq", &["rabbitmq"]),
    ("redis", &["redis"]),
    ("supabase", &["supabase-db"]),
];
/// UI services allowed on data_net besides `PACKAGE_REQUIRES` consumers.
const DATA_CLIENT_UI_SERVICES: &[&str] = &[
    "adminer",
    "appsmith",
    "chromadb_admin",
    "host-bridge",
    "n8n",
    "node-red",
    "redisinsight",
];

fn repo() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .to_path_buf()
}

fn compose_files() -> Vec<(String, String)> {
    let mut files: Vec<(String, String)> = fs::read_dir(repo())
        .unwrap()
        .flatten()
        .filter_map(|e| {
            let text = fs::read_to_string(e.path().join("docker-compose.yml")).ok()?;
            Some((e.file_name().to_string_lossy().into_owned(), text))
        })
        .collect();
    files.sort();
    files
}

fn indent(line: &str) -> usize {
    line.len() - line.trim_start().len()
}

fn service_name(line: &str) -> Option<&str> {
    let name = line.strip_prefix("  ")?.strip_suffix(':')?;
    (!name.starts_with(' ')
        && !name.is_empty()
        && name
            .chars()
            .all(|c| c.is_alphanumeric() || "_.-".contains(c)))
    .then_some(name)
}

/// Each service's `restart` value, or `None` when it sets none.
fn restarts(text: &str) -> BTreeMap<String, Option<String>> {
    let (mut out, mut in_services, mut current) = (BTreeMap::new(), false, String::new());
    for line in text.lines() {
        if indent(line) == 0 && !line.trim().is_empty() {
            in_services = line.starts_with("services:");
        } else if in_services {
            if let Some(name) = service_name(line) {
                current = name.to_string();
                out.insert(current.clone(), None);
            } else if let Some(v) = line.strip_prefix("    restart:") {
                out.insert(
                    current.clone(),
                    Some(v.trim().trim_matches(|c| c == '\'' || c == '"').to_string()),
                );
            }
        }
    }
    out
}

/// Each service's networks.
fn networks(text: &str) -> BTreeMap<String, Vec<String>> {
    let (mut out, mut in_services, mut in_nets, mut current) =
        (BTreeMap::new(), false, false, String::new());
    for line in text.lines() {
        if indent(line) == 0 && !line.trim().is_empty() {
            in_services = line.starts_with("services:");
        } else if in_services {
            if let Some(name) = service_name(line) {
                current = name.to_string();
                out.insert(current.clone(), Vec::new());
                in_nets = false;
            } else if indent(line) == 4 {
                in_nets = line.trim() == "networks:";
            } else if in_nets && indent(line) == 6 {
                let item = line.trim().trim_start_matches("- ").trim_end_matches(':');
                out.get_mut(&current).unwrap().push(item.to_string());
            }
        }
    }
    out
}

#[test]
fn every_compose_directory_is_a_service_and_in_the_catalog() {
    let catalog = crate::catalog::load_catalog();
    for (dir, _) in compose_files() {
        assert!(
            SERVICES.contains(&dir.as_str()),
            "{dir} has a docker-compose.yml but is not in SERVICES"
        );
        assert!(
            catalog.contains_key(&dir),
            "{dir} is not in service_catalog.json"
        );
    }
    for name in SERVICES {
        assert!(
            repo().join(name).join("docker-compose.yml").is_file(),
            "{name} has no docker-compose.yml"
        );
    }
}

#[test]
fn catalog_containers_match_compose_services() {
    let catalog = crate::catalog::load_catalog();
    for (dir, text) in compose_files() {
        let mut found: Vec<String> = restarts(&text).into_keys().collect();
        let mut listed = catalog[&dir].containers.clone();
        found.sort();
        listed.sort();
        assert_eq!(found, listed, "{dir}");
    }
}

#[test]
fn every_service_declares_restart_and_oneshots_are_awaited() {
    for (dir, text) in compose_files() {
        let all = restarts(&text);
        let missing: Vec<&String> = all
            .iter()
            .filter(|(_, r)| r.is_none())
            .map(|(n, _)| n)
            .collect();
        assert!(missing.is_empty(), "{dir}: set restart on {missing:?}");
        for (name, restart) in &all {
            if restart.as_deref() == Some("no") {
                let awaited = text.contains(&format!(
                    "      {name}:\n        condition: service_completed_successfully"
                ));
                assert!(awaited, "{dir}: {name} uses restart 'no' but nothing waits on it with service_completed_successfully");
            }
        }
    }
}

#[test]
fn stack_scoped_names_carry_the_prefix() {
    for (dir, text) in compose_files() {
        let mut section = "";
        for line in text.lines() {
            if indent(line) == 0 && !line.trim().is_empty() {
                section = line.split(':').next().unwrap_or("");
            }
            if let Some(v) = line.trim_start().strip_prefix("container_name:") {
                assert!(
                    v.trim().trim_matches('"').starts_with(PREFIX),
                    "{dir}: {}",
                    line.trim()
                );
            }
            if let Some(v) = line.strip_prefix("    name:") {
                if section == "volumes" || section == "networks" {
                    assert!(
                        v.trim().trim_matches('"').starts_with(RESOURCE_PREFIX),
                        "{dir}: {}",
                        line.trim()
                    );
                }
            }
        }
        assert_eq!(
            text.matches("\"traefik.enable=true\"").count(),
            text.matches(STACK_LABEL).count(),
            "{dir}: every routed service needs the sandbox.stack label"
        );
        assert!(
            !text.contains("traefik.docker.network=traefik_proxy"),
            "{dir}: use the prefixed network name"
        );
    }
}

fn all_networks() -> BTreeMap<String, BTreeMap<String, Vec<String>>> {
    compose_files()
        .into_iter()
        .map(|(dir, text)| (dir, networks(&text)))
        .collect()
}

#[test]
fn data_stores_use_data_net_not_backend_net() {
    let nets = all_networks();
    for (project, stores) in DATA_STORES {
        for store in *stores {
            let n = &nets[*project][*store];
            assert!(n.iter().any(|x| x == "data_net"), "{project}/{store}");
            assert!(!n.iter().any(|x| x == "backend_net"), "{project}/{store}");
        }
    }
}

#[test]
fn only_declared_clients_join_data_net() {
    let store_names = |p: &str| {
        DATA_STORES
            .iter()
            .find(|(d, _)| *d == p)
            .map(|(_, s)| *s)
            .unwrap_or(&[])
    };
    let consumers: Vec<&str> = DATA_STORES
        .iter()
        .flat_map(|(b, _)| {
            PACKAGE_REQUIRES
                .iter()
                .filter(move |(r, _)| r == b)
                .flat_map(|(_, u)| u.iter().copied())
        })
        .collect();
    for (project, services) in all_networks() {
        for (service, nets) in services {
            if nets.iter().any(|x| x == "data_net")
                && !store_names(&project).contains(&service.as_str())
            {
                let allowed = consumers.contains(&project.as_str())
                    || DATA_CLIENT_UI_SERVICES.contains(&project.as_str())
                    || DATA_STORES.iter().any(|(d, _)| *d == project);
                assert!(allowed, "{project}/{service} joins data_net undeclared");
            }
        }
    }
}

#[test]
fn package_consumers_can_reach_data_net() {
    let nets = all_networks();
    for (backend, _) in DATA_STORES {
        for (_, users) in PACKAGE_REQUIRES.iter().filter(|(b, _)| b == backend) {
            for consumer in *users {
                let reach = nets[*consumer]
                    .values()
                    .any(|n| n.iter().any(|x| x == "data_net"));
                assert!(reach, "{consumer} needs {backend}");
            }
        }
    }
}

#[test]
fn readers_find_the_known_shapes() {
    let garage = fs::read_to_string(repo().join("garage/docker-compose.yml")).unwrap();
    assert_eq!(
        restarts(&garage)["garage-config-init"].as_deref(),
        Some("no")
    );
    assert_eq!(
        restarts(&garage)["garage"].as_deref(),
        Some("${RESTART_POLICY:-unless-stopped}")
    );
}
