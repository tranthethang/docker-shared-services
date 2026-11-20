//! Follow container logs and Docker events on background threads.

use super::state::ContainerInfo;
use std::io::{BufRead, BufReader};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::mpsc::Sender;
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;

pub const PROJECT_LABEL: &str = "com.docker.compose.project";
const RECONNECT_DELAY: Duration = Duration::from_secs(5);
/// Container actions that change what the dashboard shows. Exec events fire constantly and are ignored.
const STATE_EVENTS: &[&str] = &[
    "create",
    "start",
    "restart",
    "stop",
    "die",
    "kill",
    "destroy",
    "pause",
    "unpause",
    "health_status",
];

type Children = Arc<Mutex<Vec<Child>>>;

fn spawn_lines(
    mut cmd: Command,
    tx: Sender<String>,
    prefix: String,
    children: &Children,
) -> Option<thread::JoinHandle<()>> {
    let mut child = cmd
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .ok()?;
    let readers: Vec<Box<dyn std::io::Read + Send>> = vec![
        Box::new(child.stdout.take()?),
        Box::new(child.stderr.take()?),
    ];
    children.lock().ok()?.push(child);
    let handles: Vec<_> = readers
        .into_iter()
        .map(|r| {
            let (tx, prefix) = (tx.clone(), prefix.clone());
            thread::spawn(move || {
                for line in BufReader::new(r).lines().map_while(Result::ok) {
                    if tx.send(format!("{prefix}{line}")).is_err() {
                        break;
                    }
                }
            })
        })
        .collect();
    Some(thread::spawn(move || {
        handles.into_iter().for_each(|h| drop(h.join()))
    }))
}

/// Follow `docker logs -f` for every container of one stack. Call `stop` to end.
pub struct LogFollower {
    children: Children,
    joins: Vec<thread::JoinHandle<()>>,
}

impl LogFollower {
    pub fn start(containers: &[ContainerInfo], tail: u32, tx: Sender<String>) -> Self {
        let children: Children = Arc::default();
        let multi = containers.len() > 1;
        let joins = containers
            .iter()
            .filter_map(|c| {
                let mut cmd = Command::new("docker");
                cmd.args(["logs", "-f", "--tail", &tail.to_string(), &c.name]);
                let prefix = if multi {
                    format!("[{}] ", c.compose_service)
                } else {
                    String::new()
                };
                spawn_lines(cmd, tx.clone(), prefix, &children)
            })
            .collect();
        Self { children, joins }
    }

    pub fn stop(&mut self) {
        if let Ok(mut children) = self.children.lock() {
            children.iter_mut().for_each(|c| drop(c.kill()));
        }
        self.joins.drain(..).for_each(|j| drop(j.join()));
    }
}

impl Drop for LogFollower {
    fn drop(&mut self) {
        self.stop();
    }
}

/// Call `on_change` whenever a Compose container changes state. Reconnects when Docker goes away.
pub struct EventWatcher {
    stopped: Arc<AtomicBool>,
    child: Children,
}

impl EventWatcher {
    pub fn start(on_change: impl Fn() + Send + 'static) -> Self {
        let stopped = Arc::new(AtomicBool::new(false));
        let child: Children = Arc::default();
        let (flag, slot) = (stopped.clone(), child.clone());
        thread::spawn(move || {
            while !flag.load(Ordering::SeqCst) {
                watch_once(&slot, &on_change);
                thread::sleep(RECONNECT_DELAY);
            }
        });
        Self { stopped, child }
    }

    pub fn stop(&self) {
        self.stopped.store(true, Ordering::SeqCst);
        if let Ok(mut children) = self.child.lock() {
            children.iter_mut().for_each(|c| drop(c.kill()));
        }
    }
}

fn watch_once(slot: &Children, on_change: &dyn Fn()) {
    let spawned = Command::new("docker")
        .args([
            "events",
            "--filter",
            "type=container",
            "--filter",
            &format!("label={PROJECT_LABEL}"),
        ])
        .args(["--format", "{{.Action}}"])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .spawn();
    let Ok(mut child) = spawned else { return };
    let Some(out) = child.stdout.take() else {
        return;
    };
    if let Ok(mut guard) = slot.lock() {
        guard.clear();
        guard.push(child);
    }
    for action in BufReader::new(out).lines().map_while(Result::ok) {
        if STATE_EVENTS.contains(&action.split(':').next().unwrap_or("")) {
            on_change();
        }
    }
}

impl Drop for EventWatcher {
    fn drop(&mut self) {
        self.stop();
    }
}
