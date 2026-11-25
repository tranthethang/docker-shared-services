//! Wait until each `restart: "no"` container has exited 0.

use super::compose::compose_with;
use super::readiness::READY_TIMEOUT;
use super::Runner;
use std::time::{Duration, Instant};

const POLL: Duration = Duration::from_secs(2);
/// `<status> <health> <exit code> <restart policy>`.
const INSPECT_FORMAT: &str =
    "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}} \
     {{.State.ExitCode}} {{or .HostConfig.RestartPolicy.Name \"no\"}}";

fn strings(items: &[&str]) -> Vec<String> {
    items.iter().map(|s| s.to_string()).collect()
}

enum Shot {
    Skip,
    Pending,
    Done,
    Failed,
}

fn classify(output: &str) -> Shot {
    let parts: Vec<&str> = output.split_whitespace().collect();
    let [status, _, exit, policy, ..] = parts[..] else {
        return Shot::Pending;
    };
    if policy != "no" {
        return Shot::Skip;
    }
    let Ok(code) = exit.parse::<i64>() else {
        return Shot::Pending;
    };
    match status {
        "exited" if code == 0 => Shot::Done,
        "exited" => Shot::Failed,
        _ => Shot::Pending,
    }
}

fn service_shot(runner: &dyn Runner, service: &str) -> Shot {
    let Ok(args) = compose_with(service, &["ps", "-aq"]) else {
        return Shot::Pending;
    };
    let out = runner.run(&args);
    if !out.ok {
        return Shot::Pending;
    }
    let mut pending = false;
    for id in out.stdout.lines().map(str::trim).filter(|l| !l.is_empty()) {
        let inspected = runner.run(&strings(&["inspect", "--format", INSPECT_FORMAT, id]));
        if !inspected.ok {
            return Shot::Pending;
        }
        match classify(&inspected.stdout) {
            Shot::Skip | Shot::Done => {}
            Shot::Pending => pending = true,
            Shot::Failed => return Shot::Failed,
        }
    }
    if pending {
        Shot::Pending
    } else {
        Shot::Done
    }
}

fn wait(
    runner: &dyn Runner,
    service: &str,
    timeout: Duration,
    poll: Duration,
    say: &dyn Fn(&str),
) -> bool {
    let deadline = Instant::now() + timeout;
    loop {
        match service_shot(runner, service) {
            Shot::Done => return true,
            Shot::Failed => {
                say(&format!("❌ {service} one-shot exited with an error"));
                return false;
            }
            Shot::Pending | Shot::Skip => {
                if Instant::now() >= deadline {
                    say(&format!(
                        "❌ {service} one-shot did not exit 0 within {}s",
                        timeout.as_secs()
                    ));
                    return false;
                }
                std::thread::sleep(poll);
            }
        }
    }
}

/// Block until every one-shot container for `service` has exited 0.
pub fn wait_until_oneshots_done(runner: &dyn Runner, service: &str, say: &dyn Fn(&str)) -> bool {
    wait(runner, service, READY_TIMEOUT, POLL, say)
}

#[cfg(test)]
mod tests {
    use super::super::Output;
    use super::*;
    use std::cell::RefCell;

    struct Fake {
        inspect: RefCell<Vec<&'static str>>,
    }

    impl Runner for Fake {
        fn run(&self, args: &[String]) -> Output {
            let stdout = if args.first().map(String::as_str) == Some("inspect") {
                let mut seq = self.inspect.borrow_mut();
                let next = if seq.len() > 1 { seq.remove(0) } else { seq[0] };
                next.to_string()
            } else {
                "abc123\n".into()
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

    fn wait_seq(seq: &[&'static str], timeout_ms: u64) -> bool {
        let runner = Fake {
            inspect: RefCell::new(seq.to_vec()),
        };
        wait(
            &runner,
            "litellm",
            Duration::from_millis(timeout_ms),
            Duration::from_millis(5),
            &|_| {},
        )
    }

    #[test]
    fn long_running_container_is_not_a_oneshot() {
        assert!(wait_seq(&["running healthy 0 unless-stopped"], 50));
    }

    #[test]
    fn waits_until_oneshot_exits_0() {
        assert!(wait_seq(&["running none 0 no", "exited none 0 no"], 500));
    }

    #[test]
    fn failed_oneshot_stops_the_wait() {
        assert!(!wait_seq(&["exited none 1 no"], 500));
    }

    #[test]
    fn running_oneshot_times_out() {
        assert!(!wait_seq(&["running none 0 no"], 20));
    }
}
