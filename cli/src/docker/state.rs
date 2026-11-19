//! Container state from the `docker` CLI: status rows, log following, and events.

use super::Runner;
use crate::config::active_services;
use crate::stack::stack_name;

use super::follow::PROJECT_LABEL;
const SERVICE_LABEL: &str = "com.docker.compose.service";
const FIELDS: usize = 8;

fn inspect_format() -> String {
    format!(
        "{{{{.Name}}}}\t{{{{.State.Status}}}}\t{{{{if .State.Health}}}}{{{{.State.Health.Status}}}}{{{{else}}}}none{{{{end}}}}\t\
         {{{{.Config.Image}}}}\t{{{{index .Config.Labels \"{PROJECT_LABEL}\"}}}}\t{{{{index .Config.Labels \"{SERVICE_LABEL}\"}}}}\t\
         {{{{.State.ExitCode}}}}\t{{{{or .HostConfig.RestartPolicy.Name \"no\"}}}}"
    )
}

#[derive(Debug, Clone, PartialEq)]
pub struct ContainerInfo {
    pub name: String,
    pub status: String,
    pub health: String,
    pub image: String,
    pub compose_service: String,
    pub completed: bool,
    pub project: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ServiceStatus {
    pub name: String,
    pub state: &'static str,
    pub health: &'static str,
    pub container_count: usize,
    pub running_count: usize,
    pub containers: Vec<ContainerInfo>,
}

/// Parse one tab-separated `inspect` line. `None` when it is malformed.
pub fn parse_container(line: &str) -> Option<ContainerInfo> {
    let f: Vec<&str> = line.trim_end().split('\t').collect();
    if f.len() < FIELDS {
        return None;
    }
    let (status, exit, policy) = (f[1], f[6].parse::<i64>().ok()?, f[7]);
    let health = if f[2] == "none" && status != "running" {
        "-"
    } else {
        f[2]
    };
    Some(ContainerInfo {
        name: f[0].trim_start_matches('/').to_string(),
        status: status.to_string(),
        health: health.to_string(),
        image: f[3].to_string(),
        compose_service: if f[5].is_empty() {
            f[0].trim_start_matches('/').into()
        } else {
            f[5].into()
        },
        completed: status == "exited" && exit == 0 && (policy.is_empty() || policy == "no"),
        project: f[4].to_string(),
    })
}

fn state_label(running: usize, total: usize) -> &'static str {
    match (total, running) {
        (0, _) => "absent",
        (_, 0) => "stopped",
        (t, r) if r < t => "partial",
        _ => "running",
    }
}

fn aggregate_health(containers: &[&ContainerInfo]) -> &'static str {
    let has = |v: &str| containers.iter().any(|c| c.health == v);
    if has("unhealthy") {
        "unhealthy"
    } else if has("starting") {
        "starting"
    } else if has("healthy") {
        "healthy"
    } else if has("none") {
        "none"
    } else {
        "-"
    }
}

/// Group containers into one row per configured service, honoring the stack prefix.
pub fn build_statuses(containers: Vec<ContainerInfo>, prefix: &str) -> Vec<ServiceStatus> {
    active_services()
        .iter()
        .map(|name| {
            let own: Vec<ContainerInfo> = containers
                .iter()
                .filter(|c| c.project.strip_prefix(prefix) == Some(*name))
                .cloned()
                .collect();
            // A finished one-shot init container is neither running nor missing.
            let active: Vec<&ContainerInfo> = own.iter().filter(|c| !c.completed).collect();
            let running = active.iter().filter(|c| c.status == "running").count();
            ServiceStatus {
                name: name.to_string(),
                state: state_label(running, active.len()),
                health: aggregate_health(&active),
                container_count: active.len(),
                running_count: running,
                containers: own.clone(),
            }
        })
        .collect()
}

/// One row per service, read with `docker ps` and `docker inspect`.
pub fn list_service_statuses(runner: &dyn Runner) -> Result<Vec<ServiceStatus>, String> {
    let ids = runner.run(&["ps".into(), "-aq".into()]);
    if !ids.ok {
        return Err(format!(
            "Cannot reach Docker: {}. Is Docker running?",
            ids.stderr.trim()
        ));
    }
    let mut args: Vec<String> = vec!["inspect".into(), "--format".into(), inspect_format()];
    let list: Vec<String> = ids.stdout.split_whitespace().map(String::from).collect();
    let containers = if list.is_empty() {
        Vec::new()
    } else {
        args.extend(list);
        runner
            .run(&args)
            .stdout
            .lines()
            .filter_map(parse_container)
            .collect()
    };
    let name = stack_name()?;
    let prefix = if name.is_empty() {
        String::new()
    } else {
        format!("{name}-")
    };
    Ok(build_statuses(containers, &prefix))
}

#[cfg(test)]
#[path = "state_tests.rs"]
mod tests;
