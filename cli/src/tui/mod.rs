//! ratatui dashboard: terminal setup, the event loop, and worker threads.

pub mod app;
mod keys;
mod ops;
mod ui;

use crate::docker::follow::{EventWatcher, LogFollower};
use crate::docker::state::list_service_statuses;
use crate::docker::{label_only_reason, Docker};
use app::{App, Effect, Msg};
use crossterm::event::{self, Event, KeyEventKind};
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use crossterm::ExecutableCommand;
use ratatui::backend::CrosstermBackend;
use ratatui::Terminal;
use std::collections::BTreeMap;
use std::io::{stdout, IsTerminal, Stdout};
use std::path::Path;
use std::sync::mpsc::{self, Sender};
use std::thread;
use std::time::{Duration, Instant};

const LOG_TAIL: u32 = 200;
const POLL: Duration = Duration::from_millis(100);

/// Puts the terminal back, on normal exit and on panic.
pub(crate) struct TerminalGuard;

impl TerminalGuard {
    pub(crate) fn enter() -> Result<Self, String> {
        enable_raw_mode().map_err(|e| e.to_string())?;
        stdout()
            .execute(EnterAlternateScreen)
            .map_err(|e| e.to_string())?;
        let previous = std::panic::take_hook();
        std::panic::set_hook(Box::new(move |info| {
            restore();
            previous(info);
        }));
        Ok(Self)
    }
}

impl Drop for TerminalGuard {
    fn drop(&mut self) {
        restore();
    }
}

fn restore() {
    let _ = disable_raw_mode();
    let _ = stdout().execute(LeaveAlternateScreen);
}

fn refresh(tx: Sender<Msg>) {
    thread::spawn(move || {
        let result = list_service_statuses(&Docker).map(|rows| {
            let locked: BTreeMap<String, String> = rows
                .iter()
                .filter_map(|r| {
                    label_only_reason(Path::new("."), &r.name).map(|why| (r.name.clone(), why))
                })
                .collect();
            (rows, locked)
        });
        let _ = tx.send(Msg::Statuses(result));
    });
}

fn run_plan(plan: app::Plan, tx: Sender<Msg>) {
    thread::spawn(move || {
        let progress = |line: &str| drop(tx.send(Msg::Ops(line.to_string())));
        let result = ops::run_plan(&plan, &Docker, &progress);
        let _ = tx.send(Msg::OpsDone {
            ok: result.ok,
            message: result.message,
        });
    });
}

fn follow_logs(containers: &[crate::docker::state::ContainerInfo], tx: Sender<Msg>) -> LogFollower {
    let (line_tx, line_rx) = mpsc::channel::<String>();
    thread::spawn(move || {
        for line in line_rx {
            if tx.send(Msg::Log(line)).is_err() {
                break;
            }
        }
    });
    LogFollower::start(containers, LOG_TAIL, line_tx)
}

/// Run effects. Returns true when the app should quit.
fn apply(effects: Vec<Effect>, tx: &Sender<Msg>, logs: &mut Option<LogFollower>) -> bool {
    for effect in effects {
        match effect {
            Effect::Quit => return true,
            Effect::Refresh => refresh(tx.clone()),
            Effect::Run(plan) => run_plan(plan, tx.clone()),
            Effect::FollowLogs(containers) => *logs = Some(follow_logs(&containers, tx.clone())),
            Effect::StopLogs => *logs = None,
        }
    }
    false
}

/// Open the dashboard. `q` leaves it and restores the terminal.
pub fn run() -> Result<(), String> {
    if !stdout().is_terminal() || !std::io::stdin().is_terminal() {
        return Err(
            "the dashboard needs an interactive terminal. Use `dss --help` for commands.".into(),
        );
    }
    let _guard = TerminalGuard::enter()?;
    let mut terminal = Terminal::new(CrosstermBackend::new(stdout())).map_err(|e| e.to_string())?;
    event_loop(&mut terminal)
}

fn event_loop(terminal: &mut Terminal<CrosstermBackend<Stdout>>) -> Result<(), String> {
    let (tx, rx) = mpsc::channel::<Msg>();
    let watcher_tx = tx.clone();
    let watcher = EventWatcher::start(move || drop(watcher_tx.send(Msg::DockerEvent)));
    let mut app = App::new();
    let mut logs: Option<LogFollower> = None;
    let mut quit = apply(app.on_start(), &tx, &mut logs);
    while !quit {
        terminal
            .draw(|f| ui::draw(f, &app))
            .map_err(|e| e.to_string())?;
        if event::poll(POLL).map_err(|e| e.to_string())? {
            if let Event::Key(key) = event::read().map_err(|e| e.to_string())? {
                if key.kind == KeyEventKind::Press {
                    quit = apply(app.on_key(key), &tx, &mut logs);
                }
            }
        }
        while let Ok(msg) = rx.try_recv() {
            quit |= apply(app.on_msg(msg), &tx, &mut logs);
        }
        quit |= apply(app.tick(Instant::now()), &tx, &mut logs);
    }
    watcher.stop();
    drop(logs);
    Ok(())
}
