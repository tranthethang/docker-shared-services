use super::*;

fn line(name: &str, status: &str, health: &str, project: &str, exit: i32, policy: &str) -> String {
    format!("/{name}\t{status}\t{health}\timg\t{project}\t{name}\t{exit}\t{policy}")
}

#[test]
fn parses_inspect_lines() {
    let c = parse_container(&line("redis", "running", "healthy", "redis", 0, "always")).unwrap();
    assert_eq!(
        (c.name.as_str(), c.status.as_str(), c.health.as_str()),
        ("redis", "running", "healthy")
    );
    let stopped = parse_container(&line("redis", "exited", "none", "redis", 1, "no")).unwrap();
    assert_eq!(stopped.health, "-");
    assert!(!stopped.completed);
    assert!(
        parse_container(&line("init", "exited", "none", "redis", 0, "no"))
            .unwrap()
            .completed
    );
    assert!(parse_container("too\tshort").is_none());
}

fn info(status: &str, health: &str, project: &str, completed: bool) -> ContainerInfo {
    ContainerInfo {
        name: "c".into(),
        status: status.into(),
        health: health.into(),
        image: String::new(),
        compose_service: "c".into(),
        completed,
        project: project.into(),
    }
}

#[test]
fn builds_one_row_per_service_and_ignores_completed_oneshots() {
    let rows = build_statuses(
        vec![
            info("running", "healthy", "redis", false),
            info("exited", "-", "redis", true),
            info("running", "starting", "postgres", false),
            info("exited", "-", "postgres", false),
            info("running", "none", "unknown-project", false),
        ],
        "",
    );
    assert_eq!(rows.len(), crate::config::SERVICES.len());
    let redis = rows.iter().find(|r| r.name == "redis").unwrap();
    assert_eq!(
        (redis.state, redis.health, redis.container_count),
        ("running", "healthy", 1)
    );
    let pg = rows.iter().find(|r| r.name == "postgres").unwrap();
    assert_eq!((pg.state, pg.health), ("partial", "starting"));
    assert_eq!(
        rows.iter().find(|r| r.name == "mailpit").unwrap().state,
        "absent"
    );
}

#[test]
fn prefix_selects_only_that_stack() {
    let rows = build_statuses(
        vec![
            info("running", "none", "dev-redis", false),
            info("running", "none", "redis", false),
        ],
        "dev-",
    );
    assert_eq!(
        rows.iter()
            .find(|r| r.name == "redis")
            .unwrap()
            .container_count,
        1
    );
}

#[test]
fn state_labels() {
    assert_eq!(state_label(0, 0), "absent");
    assert_eq!(state_label(0, 2), "stopped");
    assert_eq!(state_label(1, 2), "partial");
    assert_eq!(state_label(2, 2), "running");
}
