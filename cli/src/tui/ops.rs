//! Worker-thread operations for the dashboard. Output goes to a callback, never to stdout.

use super::app::{OpKind, Plan};
use crate::config::active_services;
use crate::docker::compose::{compose_with, ensure_networks};
use crate::docker::oneshot::wait_until_oneshots_done;
use crate::docker::readiness::ensure_dependencies_ready;
use crate::docker::{label_only_reason, Runner};
use crate::env::{assignments, report::prerequisite_problems};
use std::fs;
use std::path::Path;

const MASK: &str = "***";
const LONG_VALUE: usize = 12;
const MIN_SECRET_VALUE: usize = 3;
const SECRET_WORDS: &[&str] = &[
    "PASS",
    "SECRET",
    "TOKEN",
    "KEY",
    "CREDENTIAL",
    "PRIVATE",
    "AUTH",
    "SALT",
    "DSN",
    "COOKIE",
];

pub struct OpResult {
    pub ok: bool,
    pub message: String,
}

fn fail(message: String) -> OpResult {
    OpResult { ok: false, message }
}

fn should_mask(key: &str, value: &str) -> bool {
    if value.eq_ignore_ascii_case("true")
        || value.eq_ignore_ascii_case("false")
        || value.chars().all(|c| c.is_ascii_digit())
    {
        return false;
    }
    let upper = key.to_uppercase();
    if SECRET_WORDS.iter().any(|w| upper.contains(w)) {
        return value.len() >= MIN_SECRET_VALUE;
    }
    value.len() >= LONG_VALUE
}

/// Values from the root and service `.env` files that must never reach the screen.
pub fn values_to_mask(root: &Path, services: &[&str]) -> Vec<String> {
    let mut values: Vec<String> = Vec::new();
    let files = std::iter::once(root.join(".env"))
        .chain(services.iter().map(|s| root.join(s).join(".env")));
    for path in files {
        let Ok(text) = fs::read_to_string(path) else {
            continue;
        };
        for (key, raw) in assignments(&text) {
            let value = raw
                .trim()
                .trim_matches(|c| c == '\'' || c == '"')
                .to_string();
            if should_mask(&key, &value) && !values.contains(&value) {
                values.push(value);
            }
        }
    }
    // Longest first so a value that contains another one is masked whole.
    values.sort_by_key(|v| std::cmp::Reverse(v.len()));
    values
}

pub fn mask_known_values(text: &str, values: &[String]) -> String {
    values
        .iter()
        .fold(text.to_string(), |acc, v| acc.replace(v.as_str(), MASK))
}

fn compose(runner: &dyn Runner, service: &str, args: &[&str], say: &dyn Fn(&str)) -> bool {
    let Ok(cmd) = compose_with(service, args) else {
        return false;
    };
    say(&format!("$ docker {}", cmd.join(" ")));
    runner.stream(&cmd, say)
}

/// Check prerequisites and networks for `services`. Returns a failure message, or `None`.
fn prepare(runner: &dyn Runner, services: &[String], say: &dyn Fn(&str)) -> Option<String> {
    let bad: Vec<&String> = services
        .iter()
        .filter(|s| {
            let problems = prerequisite_problems(Path::new("."), Some(s));
            problems.iter().for_each(|p| say(p));
            !problems.is_empty()
        })
        .collect();
    if !bad.is_empty() {
        return Some(format!(
            "Prerequisite checks failed for {}",
            bad.iter()
                .map(|s| s.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    ensure_networks(runner, say).err()
}

fn start_one(runner: &dyn Runner, service: &str, say: &dyn Fn(&str)) -> bool {
    if !ensure_dependencies_ready(runner, service, say) {
        return false;
    }
    say(&format!("Starting {service}…"));
    compose(runner, service, &["up", "-d"], say) && wait_until_oneshots_done(runner, service, say)
}

fn single(runner: &dyn Runner, service: &str, kind: OpKind, say: &dyn Fn(&str)) -> OpResult {
    if !active_services().contains(&service) {
        return fail(format!("Unknown service: {service}"));
    }
    if matches!(kind, OpKind::Up | OpKind::Restart) {
        if let Some(reason) = label_only_reason(Path::new("."), service) {
            return fail(format!(
                "Cannot {} {service}: {reason}",
                if kind == OpKind::Up {
                    "start"
                } else {
                    "restart"
                }
            ));
        }
    }
    let (ok, done, failed) = match kind {
        OpKind::Up => {
            if let Some(message) = prepare(runner, &[service.to_string()], say) {
                return fail(format!("Failed to start {service}: {message}"));
            }
            (start_one(runner, service, say), "started", "start")
        }
        OpKind::Down => (
            compose(runner, service, &["down"], say),
            "down",
            "bring down",
        ),
        OpKind::Stop => (compose(runner, service, &["stop"], say), "stopped", "stop"),
        OpKind::Restart => (
            compose(runner, service, &["restart"], say),
            "restarted",
            "restart",
        ),
    };
    if ok {
        OpResult {
            ok,
            message: format!("{service} {done}"),
        }
    } else {
        fail(format!("Failed to {failed} {service}"))
    }
}

fn manage(runner: &dyn Runner, up: &[String], down: &[String], say: &dyn Fn(&str)) -> OpResult {
    let mut failed: Vec<String> = Vec::new();
    for service in down {
        say(&format!("Stopping and removing {service}…"));
        if !compose(runner, service, &["down"], say) {
            failed.push(service.clone());
        }
    }
    if !up.is_empty() {
        if let Some(message) = prepare(runner, up, say) {
            return fail(message);
        }
    }
    for service in up {
        if !start_one(runner, service, say) {
            failed.push(service.clone());
            break;
        }
    }
    if failed.is_empty() {
        OpResult {
            ok: true,
            message: "All changes applied successfully".into(),
        }
    } else {
        fail(format!("Completed with errors: {}", failed.join(", ")))
    }
}

/// Run one plan. Every output line is masked before it reaches `progress`.
pub fn run_plan(plan: &Plan, runner: &dyn Runner, progress: &dyn Fn(&str)) -> OpResult {
    let names: Vec<&str> = match plan {
        Plan::Single(s, _) => vec![s.as_str()],
        Plan::Manage { up, down } => up.iter().chain(down).map(String::as_str).collect(),
    };
    let values = values_to_mask(Path::new("."), &names);
    let say = |line: &str| progress(&mask_known_values(line, &values));
    match plan {
        Plan::Single(service, kind) => single(runner, service, *kind, &say),
        Plan::Manage { up, down } => manage(runner, up, down, &say),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn masks_secret_looking_values_and_long_tokens_only() {
        assert!(should_mask("POSTGRES16_PASSWORD", "abc"));
        assert!(!should_mask("POSTGRES16_PASSWORD", "ab"));
        assert!(!should_mask("DEBUG", "true"));
        assert!(!should_mask("PORT", "5432"));
        assert!(!should_mask("HOST", "postgres"));
        assert!(should_mask("DATABASE_URL_X", "postgres://host/db"));
    }

    #[test]
    fn mask_replaces_longest_value_first() {
        let values = vec!["hunter2-long".to_string(), "hunter2".to_string()];
        assert_eq!(
            mask_known_values("pw=hunter2-long x=hunter2", &values),
            "pw=*** x=***"
        );
    }

    #[test]
    fn values_come_from_root_and_service_env_files() {
        let root = std::env::temp_dir().join(format!("dss-mask-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("redis")).unwrap();
        fs::write(
            root.join(".env"),
            "DSS_SHARED_PASSWORD='Secret-Pass-123'\nDOMAIN=x\n",
        )
        .unwrap();
        fs::write(
            root.join("redis/.env"),
            "REDIS_PASSWORD=Secret-Pass-123\nREDIS_TOKEN=tok-1\n",
        )
        .unwrap();
        assert_eq!(
            values_to_mask(&root, &["redis"]),
            ["Secret-Pass-123", "tok-1"]
        );
    }

    #[test]
    fn unknown_service_and_label_only_fail_without_docker() {
        struct Never;
        impl Runner for Never {
            fn run(&self, _: &[String]) -> crate::docker::Output {
                panic!("docker must not run")
            }
            fn stream(&self, _: &[String], _: &dyn Fn(&str)) -> bool {
                panic!("docker must not run")
            }
        }
        let r = run_plan(&Plan::Single("nope".into(), OpKind::Up), &Never, &|_| {});
        assert!(!r.ok && r.message.contains("Unknown service"));
        let r = run_plan(
            &Plan::Single("oauth2-proxy".into(), OpKind::Up),
            &Never,
            &|_| {},
        );
        assert!(!r.ok && r.message.contains("Cannot start oauth2-proxy"));
    }
}
