//! Poll `docker inspect` until a service's containers are running and healthy.

use super::compose::compose_with;
use super::{dependency_queue, Runner};
use std::path::Path;
use std::time::{Duration, Instant};

/// A database can spend its start period plus probe retries before it accepts clients.
pub const READY_TIMEOUT: Duration = Duration::from_secs(300);
const POLL: Duration = Duration::from_secs(2);
/// Prints `<status> <health> <exit code> <restart policy>`.
const INSPECT_FORMAT: &str =
    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} \
     {{.State.ExitCode}} {{or .HostConfig.RestartPolicy.Name \"no\"}}";

fn strings(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

/// A container is ready when running and healthy, or a one-shot that exited with 0.
pub fn is_container_ready(
    status: &str,
    health: &str,
    exit_code: i64,
    restart_policy: &str,
) -> bool {
    if status == "running" {
        return health == "none" || health == "healthy";
    }
    status == "exited" && exit_code == 0 && (restart_policy.is_empty() || restart_policy == "no")
}

/// Apply `is_container_ready` to one line of `INSPECT_FORMAT` output.
pub fn parse_inspect_ready(output: &str) -> bool {
    let parts: Vec<&str> = output.split_whitespace().collect();
    let [status, health, exit, policy, ..] = parts[..] else {
        return false;
    };
    exit.parse::<i64>()
        .is_ok_and(|code| is_container_ready(status, health, code, policy))
}

fn container_ids(runner: &dyn Runner, service: &str) -> Vec<String> {
    let Ok(args) = compose_with(service, &["ps", "-aq"]) else {
        return Vec::new();
    };
    let out = runner.run(&args);
    if !out.ok {
        return Vec::new();
    }
    out.stdout
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .map(String::from)
        .collect()
}

fn container_ready(runner: &dyn Runner, id: &str) -> bool {
    let out = runner.run(&strings(&["inspect", "--format", INSPECT_FORMAT, id]));
    out.ok && parse_inspect_ready(&out.stdout)
}

fn service_ready(runner: &dyn Runner, service: &str) -> bool {
    let ids = container_ids(runner, service);
    !ids.is_empty() && ids.iter().all(|id| container_ready(runner, id))
}

/// Block until every container of `service` is ready, or `timeout` passes.
pub fn wait_until_ready(
    runner: &dyn Runner,
    service: &str,
    timeout: Duration,
    poll: Duration,
    say: &dyn Fn(&str),
) -> bool {
    if container_ids(runner, service).is_empty() {
        say(&format!("❌ {service} has no containers"));
        return false;
    }
    if service_ready(runner, service) {
        return true;
    }
    say(&format!("ℹ️  Waiting until {service} is ready..."));
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        std::thread::sleep(poll);
        if service_ready(runner, service) {
            say(&format!("✅ {service} is ready"));
            return true;
        }
    }
    say(&format!(
        "❌ {service} was not ready within {}s",
        timeout.as_secs()
    ));
    false
}

/// Start missing backends in queue order, then wait until each is ready.
pub fn ensure_dependencies_ready(runner: &dyn Runner, service: &str, say: &dyn Fn(&str)) -> bool {
    for dep in dependency_queue(service, None) {
        if service_ready(runner, &dep) {
            continue;
        }
        say(&format!("ℹ️  Queuing {dep} before {service}..."));
        let problems = crate::env::report::prerequisite_problems(Path::new("."), Some(&dep));
        if !problems.is_empty() {
            problems.iter().for_each(|p| say(p));
            say(&format!(
                "❌ Cannot start {service}: prerequisite checks failed for {dep}"
            ));
            return false;
        }
        let Ok(args) = compose_with(&dep, &["up", "-d"]) else {
            return false;
        };
        if !runner.stream(&args, say) {
            say(&format!("❌ Failed to start dependency {dep}"));
            return false;
        }
        if !wait_until_ready(runner, &dep, READY_TIMEOUT, POLL, say) {
            say(&format!(
                "❌ Cannot start {service}: dependency {dep} is not ready"
            ));
            return false;
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::super::Output;
    use super::*;
    use std::cell::{Cell, RefCell};

    struct Fake {
        inspect: RefCell<Vec<&'static str>>,
        polls: Cell<usize>,
    }

    impl Runner for Fake {
        fn run(&self, args: &[String]) -> Output {
            let stdout = if args[0] == "inspect" {
                self.polls.set(self.polls.get() + 1);
                let mut seq = self.inspect.borrow_mut();
                let next = if seq.len() > 1 { seq.remove(0) } else { seq[0] };
                next.to_string()
            } else {
                "abc123\n".to_string()
            };
            Output {
                ok: true,
                stdout,
                stderr: String::new(),
            }
        }
        fn stream(&self, _: &[String], _: &dyn Fn(&str)) -> bool {
            true
        }
    }

    fn fake(seq: &[&'static str]) -> Fake {
        Fake {
            inspect: RefCell::new(seq.to_vec()),
            polls: Cell::new(0),
        }
    }

    #[test]
    fn readiness_rules() {
        assert!(is_container_ready("running", "none", 0, "no"));
        assert!(is_container_ready("running", "healthy", 0, "always"));
        assert!(!is_container_ready("running", "starting", 0, "no"));
        assert!(!is_container_ready("running", "unhealthy", 0, "no"));
        assert!(!is_container_ready("created", "none", 0, "no"));
        assert!(is_container_ready("exited", "none", 0, "no"));
        assert!(!is_container_ready("exited", "none", 1, "no"));
        assert!(!is_container_ready("exited", "none", 0, "always"));
    }

    #[test]
    fn parses_inspect_lines() {
        assert!(parse_inspect_ready("running healthy 0 no\n"));
        assert!(!parse_inspect_ready("running starting 0 no"));
        assert!(!parse_inspect_ready("running healthy"));
        assert!(!parse_inspect_ready("running healthy x no"));
    }

    #[test]
    fn created_container_does_not_pass_the_gate() {
        let runner = fake(&["created none 0 no"]);
        let ok = wait_until_ready(
            &runner,
            "redis",
            Duration::from_millis(30),
            Duration::from_millis(5),
            &|_| {},
        );
        assert!(!ok);
        assert!(
            runner.polls.get() > 1,
            "the gate kept polling until the timeout"
        );
    }

    #[test]
    fn running_but_unhealthy_times_out() {
        let runner = fake(&["running starting 0 no"]);
        assert!(!wait_until_ready(
            &runner,
            "postgres",
            Duration::from_millis(20),
            Duration::from_millis(5),
            &|_| {}
        ));
    }

    #[test]
    fn becomes_ready_once_healthy() {
        let runner = fake(&["running starting 0 no", "running healthy 0 no"]);
        assert!(wait_until_ready(
            &runner,
            "postgres",
            Duration::from_secs(2),
            Duration::from_millis(5),
            &|_| {}
        ));
    }

    #[test]
    fn service_without_containers_is_not_ready() {
        struct Empty;
        impl Runner for Empty {
            fn run(&self, _: &[String]) -> Output {
                Output {
                    ok: true,
                    ..Output::default()
                }
            }
            fn stream(&self, _: &[String], _: &dyn Fn(&str)) -> bool {
                true
            }
        }
        assert!(!wait_until_ready(
            &Empty,
            "redis",
            Duration::from_millis(10),
            Duration::from_millis(1),
            &|_| {}
        ));
    }
}
