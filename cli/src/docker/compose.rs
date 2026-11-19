//! `docker compose` command lines, shared networks, and config validation.

use super::{shutdown_queue, Runner};
use crate::catalog::{catalog_problems, load_catalog};
use crate::config::active_services;
use crate::stack::{network_pairs, project_name, read_env_value, stack_name, ROOT_ENV_FILE};
use std::collections::BTreeMap;
use std::path::Path;

pub const TRAEFIK_PUBLISH_FILE: &str = "traefik/docker-compose.publish.yml";

fn strings(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

/// Pure builder for the `compose` argument list (without the leading `docker`).
pub fn build_compose_args(
    project: Option<&str>,
    service: &str,
    env_files: &[String],
    publish: bool,
) -> Vec<String> {
    let mut args = strings(&["compose"]);
    if let Some(p) = project {
        args.extend(strings(&["-p", p]));
    }
    args.extend(strings(&["--project-directory", service]));
    for file in env_files {
        args.extend(strings(&["--env-file", file]));
    }
    args.extend(strings(&["-f", "docker-compose.shared.yml", "-f"]));
    args.push(format!("{service}/docker-compose.yml"));
    if publish {
        args.extend(strings(&["-f", TRAEFIK_PUBLISH_FILE]));
    }
    args
}

/// Root `.env` first, then `<service>/.env`, so a service value overrides a root value.
fn env_file_args(service: &str) -> Vec<String> {
    [ROOT_ENV_FILE.to_string(), format!("{service}/.env")]
        .into_iter()
        .filter(|p| Path::new(p).is_file())
        .collect()
}

/// Compose arguments for one service, run from the repo root.
pub fn compose_args(service: &str) -> Result<Vec<String>, String> {
    let project = if stack_name()?.is_empty() {
        None
    } else {
        Some(project_name(service)?)
    };
    let publish = service == "traefik"
        && read_env_value(Path::new("traefik/.env"), "TRAEFIK_HTTP_PORT")
            .is_some_and(|v| !v.is_empty());
    Ok(build_compose_args(
        project.as_deref(),
        service,
        &env_file_args(service),
        publish,
    ))
}

/// Compose arguments plus a trailing subcommand.
pub fn compose_with(service: &str, extra: &[&str]) -> Result<Vec<String>, String> {
    let mut args = compose_args(service)?;
    args.extend(strings(extra));
    Ok(args)
}

/// Create each missing shared network, with an auto subnet when the pool overlaps.
pub fn ensure_networks(runner: &dyn Runner, say: &dyn Fn(&str)) -> Result<(), String> {
    for pair in network_pairs()? {
        let (name, subnet) = pair.split_once(':').ok_or("bad network pair")?;
        if runner.run(&strings(&["network", "inspect", name])).ok {
            continue;
        }
        say(&format!("ℹ️  Creating network {name}..."));
        let made = runner.run(&strings(&[
            "network", "create", name, "--subnet", subnet, "--driver", "bridge",
        ]));
        if made.ok {
            say(&format!("✅ Network {name} created ({subnet})"));
            continue;
        }
        let err = made.stderr.to_lowercase();
        if !(err.contains("overlap") || err.contains("pool")) {
            return Err(format!(
                "could not create network {name}: {}",
                made.stderr.trim()
            ));
        }
        say(&format!("⚠️  Subnet {subnet} for {name} overlaps another Docker address pool; using an auto-assigned subnet."));
        let auto = runner.run(&strings(&["network", "create", name, "--driver", "bridge"]));
        if !auto.ok {
            return Err(format!(
                "could not create network {name}: {}",
                auto.stderr.trim()
            ));
        }
        say(&format!("✅ Network {name} created (auto subnet)"));
    }
    Ok(())
}

fn lines(text: &str) -> Vec<String> {
    text.lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .map(String::from)
        .collect()
}

/// Compose service names in a stack directory (`otel` -> grafana, loki, alloy).
pub fn stack_services(runner: &dyn Runner, service: &str) -> Vec<String> {
    let Ok(args) = compose_with(service, &["config", "--services"]) else {
        return vec![service.into()];
    };
    let out = runner.run(&args);
    let names = if out.ok {
        lines(&out.stdout)
    } else {
        Vec::new()
    };
    if names.is_empty() {
        vec![service.into()]
    } else {
        names
    }
}

/// Services in shutdown order.
pub fn sort_for_shutdown(services: &[String]) -> Vec<String> {
    shutdown_queue(services)
}

/// Run `compose config` for every service, then check the catalog. Returns failures.
pub fn validate_all(runner: &dyn Runner, say: &dyn Fn(&str)) -> Vec<String> {
    say("Validating Docker Compose configuration...");
    let mut failed = Vec::new();
    let mut compose_services: BTreeMap<String, Vec<String>> = BTreeMap::new();
    let mut sorted: Vec<&str> = active_services().to_vec();
    sorted.sort_unstable();
    for service in sorted {
        let file = format!("{service}/docker-compose.yml");
        if !Path::new(&file).is_file() {
            say(&format!("❌ {service}: missing {file}"));
            failed.push(service.to_string());
            continue;
        }
        let Ok(args) = compose_with(service, &["config"]) else {
            continue;
        };
        let out = runner.run(&args);
        let stderr = out.stderr.trim();
        if !out.ok {
            say(&format!("❌ {service}: invalid\n{stderr}"));
            failed.push(service.to_string());
            continue;
        }
        if !stderr.is_empty() {
            say(&format!(
                "⚠️  {service}: {}",
                stderr.lines().next().unwrap_or("")
            ));
            failed.push(service.to_string());
        }
        compose_services.insert(service.to_string(), stack_services(runner, service));
    }
    say("Validating service catalog (cli/service_catalog.json)...");
    let problems = catalog_problems(&load_catalog(), &compose_services);
    problems.iter().for_each(|p| say(&format!("❌ {p}")));
    if !problems.is_empty() {
        failed.push("service_catalog.json".into());
    }
    failed
}

#[cfg(test)]
#[path = "compose_tests.rs"]
mod tests;
