use super::*;
use crate::docker::stats::{ContainerStat, DiskUsage, DockerCapacity};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

fn key(c: char) -> KeyEvent {
    KeyEvent::new(KeyCode::Char(c), KeyModifiers::NONE)
}
fn code(c: KeyCode) -> KeyEvent {
    KeyEvent::new(c, KeyModifiers::NONE)
}

fn row(name: &str, running: usize, total: usize) -> ServiceStatus {
    ServiceStatus {
        name: name.into(),
        state: if running > 0 { "running" } else { "absent" },
        health: "none",
        container_count: total,
        running_count: running,
        containers: (0..total)
            .map(|i| ContainerInfo {
                name: format!("{name}-{i}"),
                status: "running".into(),
                health: "none".into(),
                image: "img".into(),
                compose_service: name.into(),
                completed: false,
                project: name.into(),
            })
            .collect(),
    }
}

fn loaded() -> App {
    let mut app = App::new();
    app.on_start();
    let rows = vec![
        row("postgres", 1, 1),
        row("redis", 0, 0),
        row("hindsight", 0, 0),
        row("oauth2-proxy", 0, 0),
    ];
    let locked = BTreeMap::from([(
        "oauth2-proxy".to_string(),
        "OIDC client not set".to_string(),
    )]);
    app.on_msg(Msg::Statuses(Ok((rows, locked))));
    app
}

fn select_service(app: &mut App, name: &str) {
    app.selected = app
        .tree_rows()
        .iter()
        .position(|t| matches!(t, TreeRow::Service { index } if app.rows[*index].name == name))
        .unwrap();
}

#[test]
fn start_refresh_and_error() {
    let mut app = App::new();
    assert_eq!(app.on_start(), [Effect::Refresh]);
    assert!(app.on_start().is_empty());
    let effects = app.on_msg(Msg::Statuses(Ok((
        vec![row("redis", 0, 0)],
        BTreeMap::new(),
    ))));
    assert_eq!(effects, [Effect::Refresh]);
    assert_eq!(app.rows.len(), 1);
    app.on_msg(Msg::Statuses(Err("Cannot reach Docker".into())));
    assert!(app.rows.is_empty() && app.status == "Cannot reach Docker");
}

#[test]
fn cursor_moves_and_clamps() {
    let mut app = loaded();
    let last = app.tree_rows().len() - 1;
    app.on_key(key('j'));
    app.on_key(code(KeyCode::Down));
    assert_eq!(app.selected, 3);
    (0..20).for_each(|_| drop(app.on_key(key('j'))));
    assert_eq!(app.selected, last);
    (0..20).for_each(|_| drop(app.on_key(key('k'))));
    assert_eq!(app.selected, 0);
}

#[test]
fn filter_and_quit_keys() {
    let mut app = loaded();
    app.on_key(key('/'));
    assert!(app.filter_mode);
    assert!(
        app.on_key(key('r')).is_empty()
            && app.on_key(key('e')).is_empty()
            && app.on_key(key('d')).is_empty()
    );
    assert_eq!(app.visible().len(), 1);
    assert_eq!(app.visible()[0].name, "redis");
    app.on_key(code(KeyCode::Backspace));
    assert_eq!(app.filter, "re");
    app.on_key(code(KeyCode::Esc));
    assert!(!app.filter_mode);
    assert_eq!(loaded().on_key(key('q')), [Effect::Quit]);
    assert_eq!(
        loaded().on_key(KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL)),
        [Effect::Quit]
    );
}

#[test]
fn up_stop_restart_run_at_once_and_block_while_busy() {
    let mut app = loaded();
    assert_eq!(
        app.on_key(key('u')),
        [Effect::Run(Plan::Single("postgres".into(), OpKind::Up))]
    );
    assert!(app.busy);
    assert!(app.on_key(key('s')).is_empty() && app.status.contains("Busy"));
    let effects = app.on_msg(Msg::OpsDone {
        ok: true,
        message: "postgres started".into(),
    });
    assert_eq!(effects, [Effect::Refresh]);
    assert!(!app.busy);
    assert_eq!(
        app.on_key(key('s')),
        [Effect::Run(Plan::Single("postgres".into(), OpKind::Stop))]
    );
    app.on_msg(Msg::OpsDone {
        ok: true,
        message: "ok".into(),
    });
    assert_eq!(
        app.on_key(key('r')),
        [Effect::Run(Plan::Single(
            "postgres".into(),
            OpKind::Restart
        ))]
    );
}

#[test]
fn down_and_label_only_rules() {
    let mut app = loaded();
    assert!(app.on_key(key('d')).is_empty());
    assert!(matches!(app.modal, Some(Modal::Confirm { .. })));
    assert!(app.on_key(key('n')).is_empty() && app.modal.is_none() && !app.busy);
    app.on_key(key('d'));
    assert_eq!(
        app.on_key(key('y')),
        [Effect::Run(Plan::Single("postgres".into(), OpKind::Down))]
    );
    assert!(app.busy);
    select_service(&mut app, "oauth2-proxy");
    app.busy = false;
    assert!(app.on_key(key('u')).is_empty() && app.status.contains("label only"));
    assert!(app.on_key(key('r')).is_empty());
    assert!(app.on_key(key(' ')).is_empty() && !app.manage.contains("oauth2-proxy"));
}

#[test]
fn space_then_m_builds_a_plan_in_startup_order() {
    let mut app = loaded();
    select_service(&mut app, "redis");
    app.on_key(key(' '));
    select_service(&mut app, "hindsight");
    app.on_key(key(' '));
    assert_eq!(app.manage.len(), 3);
    app.on_key(key('m'));
    let Some(Modal::Confirm { plan, .. }) = app.modal.clone() else {
        panic!("expected confirm")
    };
    assert_eq!(
        plan,
        Plan::Manage {
            up: vec!["redis".into(), "hindsight".into()],
            down: vec![]
        }
    );
    assert_eq!(app.on_key(key('y')), [Effect::Run(plan)]);
}

#[test]
fn deselecting_a_running_service_plans_a_stop() {
    let mut app = loaded();
    assert_eq!(app.manage.iter().collect::<Vec<_>>(), ["postgres"]);
    app.on_key(key(' '));
    app.on_key(key('m'));
    let Some(Modal::Confirm { plan, .. }) = app.modal.clone() else {
        panic!("expected confirm")
    };
    assert_eq!(
        plan,
        Plan::Manage {
            up: vec![],
            down: vec!["postgres".into()]
        }
    );
}

#[test]
fn manage_selection_no_changes_select_all_clear_and_refresh() {
    let mut app = loaded();
    assert!(app.on_key(key('m')).is_empty() && app.status == "No changes needed");
    app.on_key(key('a'));
    assert_eq!(app.manage.len(), 3);
    assert!(!app.manage.contains("oauth2-proxy"));
    app.on_key(key('c'));
    assert!(app.manage.is_empty());
    select_service(&mut app, "redis");
    app.on_key(key(' '));
    app.on_start();
    app.on_msg(Msg::Statuses(Ok((app.rows.clone(), app.locked.clone()))));
    assert!(app.manage.contains("redis"));
}

#[test]
fn logs_follow_stop_and_cap() {
    let mut app = loaded();
    let effects = app.on_key(key('l'));
    assert!(matches!(&effects[..], [Effect::FollowLogs(c)] if c.len() == 1));
    assert_eq!(app.log_target.as_deref(), Some("postgres"));
    (0..LOG_MAX_LINES + 50).for_each(|i| drop(app.on_msg(Msg::Log(i.to_string()))));
    assert_eq!(app.logs.len(), LOG_MAX_LINES);
    assert_eq!(app.logs.front().unwrap(), "50");
    assert_eq!(app.on_key(key('l')), [Effect::StopLogs]);
    assert!(app.log_target.is_none() && app.logs.is_empty());
    select_service(&mut app, "redis");
    assert!(app.on_key(key('l')).is_empty());
}

#[test]
fn docker_events_are_debounced_into_one_refresh() {
    let mut app = loaded();
    let t0 = Instant::now();
    app.on_event(t0);
    app.on_event(t0 + Duration::from_millis(100));
    assert!(app.tick(t0 + Duration::from_millis(200)).is_empty());
    assert_eq!(app.tick(t0 + Duration::from_millis(400)), [Effect::Refresh]);
    assert!(app.tick(t0 + Duration::from_millis(900)).is_empty());
}

#[test]
fn help_and_shift_r() {
    let mut app = loaded();
    app.on_key(key('?'));
    assert_eq!(app.modal, Some(Modal::Help));
    app.on_key(code(KeyCode::Esc));
    assert!(app.modal.is_none());
    assert_eq!(app.on_key(key('R')), [Effect::Refresh]);
    app.on_msg(Msg::Statuses(Ok((app.rows.clone(), app.locked.clone()))));
    app.busy = true;
    assert!(app.on_key(key('R')).is_empty());
}

#[test]
fn active_zoom_open_and_presets_shortcuts() {
    let mut app = loaded();
    app.on_key(key('f'));
    assert!(app.active_only && app.visible().len() == 1);
    app.on_key(key('f'));
    assert!(!app.active_only && app.visible().len() == 4);
    app.on_key(key('z'));
    assert!(app.zoom_details);
    assert!(app.on_key(key('o')).is_empty()); // postgres has no web_ui
    select_service(&mut app, "hindsight");
    assert!(
        matches!(app.on_key(key('o')).as_slice(), [Effect::OpenUrl(u)] if u.starts_with("https://"))
    );
    app.on_key(key('p'));
    assert_eq!(app.modal, Some(Modal::Presets { selected: 0 }));
    app.on_key(code(KeyCode::Enter));
    assert!(app.modal.is_none() && app.manage.contains("postgres") && app.manage_dirty);
}

#[test]
fn telemetry_messages_update_app_state() {
    let mut app = loaded();
    app.on_msg(Msg::Capacity(DockerCapacity {
        ncpu: 4,
        mem_total_bytes: 8_000_000_000,
    }));
    app.on_msg(Msg::DiskUsage(DiskUsage {
        total_bytes: 5_000_000_000,
        ..DiskUsage::default()
    }));
    let stats = BTreeMap::from([(
        "postgres-0".to_string(),
        ContainerStat {
            name: "postgres-0".into(),
            cpu_pct: 12.5,
            mem_used_bytes: 100_000,
            ..ContainerStat::default()
        },
    )]);
    app.on_msg(Msg::Stats(stats));
    assert_eq!(app.capacity.unwrap().ncpu, 4);
    assert_eq!(app.disk_usage.unwrap().total_bytes, 5_000_000_000);
    assert_eq!(app.cpu_history.back().copied(), Some(12.5));
    assert_eq!(app.service_stats(&app.rows[0]), (12.5, 100_000));
}
