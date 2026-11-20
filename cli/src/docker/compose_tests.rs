use super::*;
use std::cell::RefCell;

type Reply = Box<dyn Fn(&[String]) -> super::super::Output>;

struct Fake {
    calls: RefCell<Vec<Vec<String>>>,
    reply: Reply,
}

impl Runner for Fake {
    fn run(&self, args: &[String]) -> super::super::Output {
        self.calls.borrow_mut().push(args.to_vec());
        (self.reply)(args)
    }
    fn stream(&self, args: &[String], _: &dyn Fn(&str)) -> bool {
        self.run(args).ok
    }
}

fn out(ok: bool, stdout: &str, stderr: &str) -> super::super::Output {
    super::super::Output {
        ok,
        stdout: stdout.into(),
        stderr: stderr.into(),
    }
}

#[test]
fn builds_args_with_project_env_files_and_publish() {
    let args = build_compose_args(
        Some("dev-traefik"),
        "traefik",
        &strings(&[".env", "traefik/.env"]),
        true,
    );
    assert_eq!(
        args.join(" "),
        "compose -p dev-traefik --project-directory traefik --env-file .env --env-file traefik/.env \
         -f docker-compose.shared.yml -f traefik/docker-compose.yml -f traefik/docker-compose.publish.yml"
    );
    let plain = build_compose_args(None, "redis", &[], false);
    assert_eq!(
        plain[..3],
        strings(&["compose", "--project-directory", "redis"])[..]
    );
}

#[test]
fn stack_services_falls_back_to_the_service_name() {
    let fake = Fake {
        calls: RefCell::default(),
        reply: Box::new(|_| out(false, "", "boom")),
    };
    assert_eq!(stack_services(&fake, "redis"), ["redis"]);
    let ok = Fake {
        calls: RefCell::default(),
        reply: Box::new(|_| out(true, "grafana\n loki \n\nalloy\n", "")),
    };
    assert_eq!(stack_services(&ok, "otel"), ["grafana", "loki", "alloy"]);
}

#[test]
fn ensure_networks_creates_missing_and_retries_on_overlap() {
    let fake = Fake {
        calls: RefCell::default(),
        reply: Box::new(|args| match args[1].as_str() {
            "inspect" => out(false, "", "no such network"),
            _ if args.contains(&"--subnet".to_string()) => {
                out(false, "", "Pool overlaps with other one")
            }
            _ => out(true, "", ""),
        }),
    };
    ensure_networks(&fake, &|_| {}).unwrap();
    let calls = fake.calls.borrow();
    assert_eq!(
        calls.len(),
        9,
        "inspect, create with subnet, create auto for each of 3 networks"
    );
    assert!(calls
        .iter()
        .any(|c| c.join(" ") == "network create data_net --driver bridge"));
}

#[test]
fn ensure_networks_fails_on_other_errors_and_skips_existing() {
    let bad = Fake {
        calls: RefCell::default(),
        reply: Box::new(|args| {
            if args[1] == "inspect" {
                out(false, "", "")
            } else {
                out(false, "", "permission denied")
            }
        }),
    };
    assert!(ensure_networks(&bad, &|_| {})
        .unwrap_err()
        .contains("permission denied"));
    let exists = Fake {
        calls: RefCell::default(),
        reply: Box::new(|_| out(true, "", "")),
    };
    ensure_networks(&exists, &|_| {}).unwrap();
    assert_eq!(exists.calls.borrow().len(), 3);
}
