use super::*;
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

fn key(c: char) -> KeyEvent {
    KeyEvent::new(KeyCode::Char(c), KeyModifiers::NONE)
}

fn code(code: KeyCode) -> KeyEvent {
    KeyEvent::new(code, KeyModifiers::NONE)
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

#[test]
fn start_requests_one_refresh_and_loads_rows() {
    let mut app = App::new();
    assert_eq!(app.on_start(), [Effect::Refresh]);
    assert!(app.on_start().is_empty(), "a refresh is already running");
    let effects = app.on_msg(Msg::Statuses(Ok((
        vec![row("redis", 0, 0)],
        BTreeMap::new(),
    ))));
    assert_eq!(effects, [Effect::Refresh], "the late request reruns once");
    assert_eq!(app.rows.len(), 1);
}

#[test]
fn docker_error_clears_rows_and_shows_message() {
    let mut app = loaded();
    app.on_msg(Msg::Statuses(Err("Cannot reach Docker".into())));
    assert!(app.rows.is_empty());
    assert_eq!(app.status, "Cannot reach Docker");
}

#[test]
fn cursor_moves_and_clamps() {
    let mut app = loaded();
    app.on_key(key('j'));
    app.on_key(code(KeyCode::Down));
    assert_eq!(app.selected, 2);
    (0..10).for_each(|_| drop(app.on_key(key('j'))));
    assert_eq!(app.selected, 3);
    (0..10).for_each(|_| drop(app.on_key(key('k'))));
    assert_eq!(app.selected, 0);
}

#[test]
fn filter_narrows_rows_and_esc_returns_to_the_list() {
    let mut app = loaded();
    app.on_key(key('/'));
    assert!(app.filter_mode);
    "red".chars().for_each(|c| drop(app.on_key(key(c))));
    assert_eq!(app.visible().len(), 1);
    assert_eq!(app.selected_row().unwrap().name, "redis");
    app.on_key(code(KeyCode::Backspace));
    assert_eq!(app.filter, "re");
    app.on_key(code(KeyCode::Esc));
    assert!(!app.filter_mode);
    app.on_key(key('q'));
}

#[test]
fn typing_in_filter_mode_does_not_trigger_actions() {
    let mut app = loaded();
    app.on_key(key('/'));
    assert!(app.on_key(key('q')).is_empty());
    assert!(app.on_key(key('u')).is_empty());
    assert_eq!(app.filter, "qu");
}

#[test]
fn q_and_ctrl_c_quit() {
    assert_eq!(loaded().on_key(key('q')), [Effect::Quit]);
    let ctrl_c = KeyEvent::new(KeyCode::Char('c'), KeyModifiers::CONTROL);
    assert_eq!(loaded().on_key(ctrl_c), [Effect::Quit]);
}

#[test]
fn up_stop_restart_run_at_once_and_block_while_busy() {
    let mut app = loaded();
    assert_eq!(
        app.on_key(key('u')),
        [Effect::Run(Plan::Single("postgres".into(), OpKind::Up))]
    );
    assert!(app.busy);
    assert!(app.on_key(key('s')).is_empty());
    assert!(app.status.contains("Busy"));
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
fn down_asks_for_confirmation() {
    let mut app = loaded();
    assert!(app.on_key(key('d')).is_empty());
    assert!(matches!(app.modal, Some(Modal::Confirm { .. })));
    assert!(app.on_key(key('n')).is_empty());
    assert!(app.modal.is_none() && !app.busy);
    app.on_key(key('d'));
    let effects = app.on_key(key('y'));
    assert_eq!(
        effects,
        [Effect::Run(Plan::Single("postgres".into(), OpKind::Down))]
    );
    assert!(app.busy);
}

#[test]
fn label_only_rows_refuse_up_restart_and_manage_toggle() {
    let mut app = loaded();
    (0..3).for_each(|_| drop(app.on_key(key('j'))));
    assert_eq!(app.selected_row().unwrap().name, "oauth2-proxy");
    assert!(app.on_key(key('u')).is_empty());
    assert!(app.status.contains("label only"));
    assert!(app.on_key(key('r')).is_empty());
    assert!(app.on_key(key(' ')).is_empty());
    assert!(!app.manage.contains("oauth2-proxy"));
}

#[test]
fn manage_selection_starts_from_running_services() {
    let app = loaded();
    assert_eq!(app.manage.iter().collect::<Vec<_>>(), ["postgres"]);
}

#[test]
fn space_then_m_builds_a_plan_in_startup_order() {
    let mut app = loaded();
    app.on_key(key('j'));
    app.on_key(key(' '));
    app.on_key(key('j'));
    app.on_key(key(' '));
    assert_eq!(app.manage.len(), 3);
    app.on_key(key('m'));
    let Some(Modal::Confirm { plan, .. }) = app.modal.clone() else {
        panic!("expected a confirm modal")
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
    app.on_key(key(' '));
    app.on_key(key('m'));
    let Some(Modal::Confirm { plan, .. }) = app.modal.clone() else {
        panic!("expected a confirm modal")
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
fn manage_with_no_changes_says_so() {
    let mut app = loaded();
    assert!(app.on_key(key('m')).is_empty());
    assert_eq!(app.status, "No changes needed");
    assert!(app.modal.is_none());
}

#[test]
fn select_all_skips_locked_and_clear_empties() {
    let mut app = loaded();
    app.on_key(key('a'));
    assert_eq!(app.manage.len(), 3);
    assert!(!app.manage.contains("oauth2-proxy"));
    app.on_key(key('c'));
    assert!(app.manage.is_empty());
}

#[test]
fn dirty_manage_selection_survives_a_refresh() {
    let mut app = loaded();
    app.on_key(key('j'));
    app.on_key(key(' '));
    app.on_start();
    app.on_msg(Msg::Statuses(Ok((app.rows.clone(), app.locked.clone()))));
    assert!(app.manage.contains("redis"));
}

#[test]
fn logs_toggle_follows_and_stops() {
    let mut app = loaded();
    let effects = app.on_key(key('l'));
    assert!(matches!(&effects[..], [Effect::FollowLogs(c)] if c.len() == 1));
    assert_eq!(app.log_target.as_deref(), Some("postgres"));
    app.on_msg(Msg::Log("hello".into()));
    assert_eq!(app.logs.len(), 1);
    assert_eq!(app.on_key(key('l')), [Effect::StopLogs]);
    assert!(app.log_target.is_none() && app.logs.is_empty());
    app.on_key(key('j'));
    assert!(app.on_key(key('l')).is_empty(), "redis has no containers");
}

#[test]
fn log_buffer_is_capped() {
    let mut app = loaded();
    for i in 0..LOG_MAX_LINES + 50 {
        app.on_msg(Msg::Log(i.to_string()));
    }
    assert_eq!(app.logs.len(), LOG_MAX_LINES);
    assert_eq!(app.logs.front().unwrap(), "50");
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
fn help_modal_opens_and_closes() {
    let mut app = loaded();
    app.on_key(key('?'));
    assert_eq!(app.modal, Some(Modal::Help));
    assert!(app.on_key(key('x')).is_empty() && app.modal.is_some());
    app.on_key(code(KeyCode::Esc));
    assert!(app.modal.is_none());
}

#[test]
fn shift_r_refreshes_unless_busy() {
    let mut app = loaded();
    assert_eq!(app.on_key(key('R')), [Effect::Refresh]);
    app.on_msg(Msg::Statuses(Ok((app.rows.clone(), app.locked.clone()))));
    app.busy = true;
    assert!(app.on_key(key('R')).is_empty());
}
