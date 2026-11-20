//! Docker process runner, dependency ordering, and the start gate.

pub mod compose;
pub mod follow;
pub mod readiness;
pub mod state;
pub mod stats;

use crate::config::{PACKAGE_REQUIRES, START_ORDER};
use crate::stack::read_env_value;
use std::io::{BufRead, BufReader};
use std::path::Path;
use std::process::{Command, Stdio};
use std::sync::mpsc;
use std::thread;

/// Captured result of one `docker` call.
#[derive(Debug, Clone, Default)]
pub struct Output {
    pub ok: bool,
    pub stdout: String,
    pub stderr: String,
}

/// Runs `docker <args>`. Tests replace it with a fake.
pub trait Runner {
    /// Run and capture output.
    fn run(&self, args: &[String]) -> Output;
    /// Run and pass each output line to `on_line` while the process works.
    fn stream(&self, args: &[String], on_line: &dyn Fn(&str)) -> bool;
}

/// The real runner, built on `std::process::Command`.
pub struct Docker;

impl Runner for Docker {
    fn run(&self, args: &[String]) -> Output {
        match Command::new("docker").args(args).output() {
            Ok(out) => Output {
                ok: out.status.success(),
                stdout: String::from_utf8_lossy(&out.stdout).into_owned(),
                stderr: String::from_utf8_lossy(&out.stderr).into_owned(),
            },
            Err(e) => Output {
                ok: false,
                stdout: String::new(),
                stderr: e.to_string(),
            },
        }
    }

    fn stream(&self, args: &[String], on_line: &dyn Fn(&str)) -> bool {
        let spawned = Command::new("docker")
            .args(args)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn();
        let Ok(mut child) = spawned else {
            on_line("docker: command not found");
            return false;
        };
        let (tx, rx) = mpsc::channel::<String>();
        let mut readers = Vec::new();
        if let Some(out) = child.stdout.take() {
            readers.push(pump(out, tx.clone()));
        }
        if let Some(err) = child.stderr.take() {
            readers.push(pump(err, tx.clone()));
        }
        drop(tx);
        for line in rx {
            on_line(&line);
        }
        readers.into_iter().for_each(|r| {
            let _ = r.join();
        });
        child.wait().is_ok_and(|s| s.success())
    }
}

fn pump(
    source: impl std::io::Read + Send + 'static,
    tx: mpsc::Sender<String>,
) -> thread::JoinHandle<()> {
    thread::spawn(move || {
        for line in BufReader::new(source).lines().map_while(Result::ok) {
            if tx.send(line).is_err() {
                break;
            }
        }
    })
}

fn order_key(name: &str) -> (usize, String) {
    let index = START_ORDER.iter().position(|s| *s == name).unwrap_or(999);
    (index, name.to_string())
}

/// Backends `service` must reach before it starts. `available` limits the set.
pub fn direct_dependencies(service: &str, available: Option<&[String]>) -> Vec<String> {
    let mut found: Vec<String> = PACKAGE_REQUIRES
        .iter()
        .filter(|(backend, users)| *backend != service && users.contains(&service))
        .filter(|(backend, _)| available.is_none_or(|a| a.iter().any(|x| x == backend)))
        .map(|(backend, _)| backend.to_string())
        .collect();
    found.sort_by_key(|n| order_key(n));
    found.dedup();
    found
}

/// Transitive backends that must be ready before `service`, in startup order.
pub fn dependency_queue(service: &str, available: Option<&[String]>) -> Vec<String> {
    fn walk(name: &str, available: Option<&[String]>, seen: &mut Vec<String>) {
        for dep in direct_dependencies(name, available) {
            if !seen.contains(&dep) {
                walk(&dep, available, seen);
                seen.push(dep);
            }
        }
    }
    let mut seen = Vec::new();
    walk(service, available, &mut seen);
    startup_queue(&seen)
}

/// Dependency order, using `START_ORDER` when several services are ready together.
pub fn startup_queue(services: &[String]) -> Vec<String> {
    let mut remaining: Vec<String> = Vec::new();
    for s in services {
        if !remaining.contains(s) {
            remaining.push(s.clone());
        }
    }
    let deps: Vec<(String, Vec<String>)> = remaining
        .iter()
        .map(|n| (n.clone(), direct_dependencies(n, Some(&remaining))))
        .collect();
    let mut queued = Vec::new();
    while !remaining.is_empty() {
        let mut ready: Vec<String> = deps
            .iter()
            .filter(|(n, d)| remaining.contains(n) && d.iter().all(|x| !remaining.contains(x)))
            .map(|(n, _)| n.clone())
            .collect();
        if ready.is_empty() {
            // A cycle cannot happen with the static table. Fall back to START_ORDER.
            remaining.sort_by_key(|n| order_key(n));
            queued.append(&mut remaining);
            break;
        }
        ready.sort_by_key(|n| order_key(n));
        remaining.retain(|n| *n != ready[0]);
        queued.push(ready.swap_remove(0));
    }
    queued
}

/// Reverse startup order for shutdown. Traefik always stops last.
pub fn shutdown_queue(services: &[String]) -> Vec<String> {
    let key = |s: &String| -> (i64, usize, String) {
        if s == "traefik" {
            return (-1, 0, s.clone());
        }
        (0, order_key(s).0.min(500), s.clone())
    };
    let mut sorted = services.to_vec();
    sorted.sort_by_key(key);
    sorted.reverse();
    sorted
}

const OAUTH2_REASON: &str =
    "OIDC client not set — fill OAUTH2_PROXY_CLIENT_ID and OAUTH2_PROXY_CLIENT_SECRET in oauth2-proxy/.env";

/// Why `service` is display-only, or `None` when it can start.
pub fn label_only_reason(root: &Path, service: &str) -> Option<String> {
    if service != "oauth2-proxy" {
        return None;
    }
    let env = root.join("oauth2-proxy/.env");
    if !env.is_file() {
        return Some("oauth2-proxy/.env is missing — run make setup".into());
    }
    let unset = |key| read_env_value(&env, key).is_none_or(|v| v.is_empty());
    (unset("OAUTH2_PROXY_CLIENT_ID") || unset("OAUTH2_PROXY_CLIENT_SECRET"))
        .then(|| OAUTH2_REASON.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn names(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn direct_dependencies_come_from_the_requires_table() {
        assert_eq!(direct_dependencies("hindsight", None), ["pgvector"]);
        assert_eq!(direct_dependencies("inngest", None), ["postgres", "redis"]);
        assert!(direct_dependencies("postgres", None).is_empty());
        assert_eq!(
            direct_dependencies("inngest", Some(&names(&["redis"]))),
            ["redis"]
        );
    }

    #[test]
    fn queue_resolves_transitively_in_start_order() {
        assert_eq!(dependency_queue("garage_ui", None), ["garage"]);
        assert_eq!(dependency_queue("zitadel", None), ["postgres"]);
        assert!(dependency_queue("adminer", None).is_empty());
    }

    #[test]
    fn startup_queue_orders_selection_and_dedups() {
        let queue = startup_queue(&names(&[
            "hindsight",
            "redis",
            "pgvector",
            "traefik",
            "redis",
        ]));
        assert_eq!(queue, ["traefik", "pgvector", "redis", "hindsight"]);
        let unknown = startup_queue(&names(&["zz", "aa", "postgres"]));
        assert_eq!(unknown, ["postgres", "aa", "zz"]);
    }

    #[test]
    fn shutdown_is_reverse_of_startup_with_traefik_last() {
        let down = shutdown_queue(&names(&["redis", "traefik", "postgres", "hasura"]));
        assert_eq!(down, ["hasura", "redis", "postgres", "traefik"]);
    }

    #[test]
    fn oauth2_proxy_gate_blocks_without_credentials() {
        let root = std::env::temp_dir().join(format!("dss-gate-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        assert_eq!(label_only_reason(&root, "redis"), None);
        assert!(label_only_reason(&root, "oauth2-proxy")
            .unwrap()
            .contains("missing"));
        let dir = root.join("oauth2-proxy");
        std::fs::create_dir_all(&dir).unwrap();
        std::fs::write(
            dir.join(".env"),
            "OAUTH2_PROXY_CLIENT_ID=abc\nOAUTH2_PROXY_CLIENT_SECRET=\n",
        )
        .unwrap();
        assert!(label_only_reason(&root, "oauth2-proxy")
            .unwrap()
            .contains("OIDC client not set"));
        std::fs::write(
            dir.join(".env"),
            "OAUTH2_PROXY_CLIENT_ID=abc\nOAUTH2_PROXY_CLIENT_SECRET=s\n",
        )
        .unwrap();
        assert_eq!(label_only_reason(&root, "oauth2-proxy"), None);
    }
}
