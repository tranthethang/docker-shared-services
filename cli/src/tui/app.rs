//! Dashboard state and key handling. No terminal or Docker calls live here.

use crate::catalog::{self, Catalog};
use crate::docker::state::{ContainerInfo, ServiceStatus};
use crate::docker::stats::{ContainerStat, DiskUsage, DockerCapacity};
use crate::stack::ROOT_ENV_FILE;
use crate::tui::theme::Theme;
use crate::tui::tree::{build_tree, TreeRow};
use std::collections::{BTreeMap, BTreeSet, VecDeque};
use std::path::Path;
use std::time::{Duration, Instant};

pub const LOG_MAX_LINES: usize = 2000;
const OPS_MAX_LINES: usize = 200;
const CPU_HISTORY_MAX: usize = 16;
const EVENT_DEBOUNCE: Duration = Duration::from_millis(300);

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum OpKind {
    Up,
    Down,
    Stop,
    Restart,
}

/// Work for the worker thread.
#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Plan {
    Single(String, OpKind),
    Manage { up: Vec<String>, down: Vec<String> },
}

#[derive(Clone, PartialEq, Eq, Debug)]
pub enum Modal {
    Help,
    Presets {
        selected: usize,
    },
    Confirm {
        title: String,
        body: String,
        plan: Plan,
    },
}

/// What the event loop must do after a key or message.
#[derive(Clone, PartialEq, Debug)]
pub enum Effect {
    Refresh,
    Run(Plan),
    FollowLogs(Vec<ContainerInfo>),
    StopLogs,
    OpenUrl(String),
    Quit,
}

/// Results that worker threads send back.
pub enum Msg {
    Statuses(Result<(Vec<ServiceStatus>, BTreeMap<String, String>), String>),
    Stats(BTreeMap<String, ContainerStat>),
    Capacity(DockerCapacity),
    DiskUsage(DiskUsage),
    Ops(String),
    OpsDone { ok: bool, message: String },
    Log(String),
    DockerEvent,
}

#[derive(Default)]
pub struct App {
    pub rows: Vec<ServiceStatus>,
    pub locked: BTreeMap<String, String>,
    pub filter: String,
    pub filter_mode: bool,
    pub selected: usize,
    pub manage: BTreeSet<String>,
    pub(super) manage_dirty: bool,
    pub(super) manage_ready: bool,
    pub busy: bool,
    pub(super) refreshing: bool,
    pub(super) refresh_again: bool,
    pub(super) event_at: Option<Instant>,
    pub status: String,
    pub ops: VecDeque<String>,
    pub logs: VecDeque<String>,
    pub log_target: Option<String>,
    pub modal: Option<Modal>,
    pub error: String,
    pub catalog: Catalog,
    pub domain: String,
    pub theme: Theme,
    pub stats: BTreeMap<String, ContainerStat>,
    pub capacity: Option<DockerCapacity>,
    pub disk_usage: Option<DiskUsage>,
    pub cpu_history: VecDeque<f64>,
    pub collapsed: BTreeSet<String>,
    pub active_only: bool,
    pub zoom_details: bool,
}

impl App {
    pub fn new() -> Self {
        Self {
            status: "Ready".into(),
            catalog: catalog::load_catalog(),
            domain: catalog::root_domain(Path::new(ROOT_ENV_FILE)),
            theme: Theme::from_env(),
            ..Self::default()
        }
    }

    pub fn tree_rows(&self) -> Vec<TreeRow> {
        build_tree(
            &self.rows,
            &self.catalog,
            &self.collapsed,
            &self.filter,
            self.active_only,
        )
    }

    pub fn selected_tree_row(&self) -> Option<TreeRow> {
        self.tree_rows().get(self.selected).cloned()
    }

    pub fn visible(&self) -> Vec<&ServiceStatus> {
        self.tree_rows()
            .into_iter()
            .filter_map(|row| match row {
                TreeRow::Service { index } => self.rows.get(index),
                TreeRow::Group { .. } => None,
            })
            .collect()
    }

    pub fn selected_row(&self) -> Option<&ServiceStatus> {
        match self.selected_tree_row() {
            Some(TreeRow::Service { index }) => self.rows.get(index),
            _ => None,
        }
    }

    pub fn service_stats(&self, row: &ServiceStatus) -> (f64, u64) {
        row.containers.iter().fold((0.0, 0), |(cpu, mem), c| {
            self.stats
                .get(&c.name)
                .map_or((cpu, mem), |s| (cpu + s.cpu_pct, mem + s.mem_used_bytes))
        })
    }

    pub fn total_usage(&self) -> (f64, u64) {
        self.stats
            .values()
            .fold((0.0, 0), |(c, m), s| (c + s.cpu_pct, m + s.mem_used_bytes))
    }

    pub(super) fn selected_name(&self) -> Option<String> {
        self.selected_row().map(|r| r.name.clone())
    }
    pub(super) fn clamp(&mut self) {
        self.selected = self.selected.min(self.tree_rows().len().saturating_sub(1));
    }

    pub(super) fn push_ops(&mut self, line: String) {
        self.ops.push_back(line);
        while self.ops.len() > OPS_MAX_LINES {
            self.ops.pop_front();
        }
    }

    pub(super) fn request_refresh(&mut self) -> Vec<Effect> {
        if self.refreshing {
            self.refresh_again = true;
            return vec![];
        }
        self.refreshing = true;
        self.status = "Refreshing service status…".into();
        vec![Effect::Refresh]
    }

    pub fn on_start(&mut self) -> Vec<Effect> {
        self.request_refresh()
    }

    pub fn on_event(&mut self, now: Instant) {
        self.event_at.get_or_insert(now);
    }

    pub fn tick(&mut self, now: Instant) -> Vec<Effect> {
        match self.event_at {
            Some(at) if now.duration_since(at) >= EVENT_DEBOUNCE => {
                self.event_at = None;
                self.request_refresh()
            }
            _ => vec![],
        }
    }

    pub fn on_msg(&mut self, msg: Msg) -> Vec<Effect> {
        match msg {
            Msg::Statuses(result) => self.apply_statuses(result),
            Msg::Stats(stats) => {
                self.cpu_history
                    .push_back(stats.values().map(|s| s.cpu_pct).sum());
                while self.cpu_history.len() > CPU_HISTORY_MAX {
                    self.cpu_history.pop_front();
                }
                self.stats = stats;
                vec![]
            }
            Msg::Capacity(cap) => {
                self.capacity = Some(cap);
                vec![]
            }
            Msg::DiskUsage(df) => {
                self.disk_usage = Some(df);
                vec![]
            }
            Msg::Ops(line) => {
                self.push_ops(line);
                vec![]
            }
            Msg::OpsDone { ok, message } => {
                self.busy = false;
                self.status = message.clone();
                self.push_ops(format!("{} {message}", if ok { "✅" } else { "❌" }));
                self.manage_dirty = false;
                self.request_refresh()
            }
            Msg::Log(line) => {
                self.logs.push_back(line);
                while self.logs.len() > LOG_MAX_LINES {
                    self.logs.pop_front();
                }
                vec![]
            }
            Msg::DockerEvent => {
                self.on_event(Instant::now());
                vec![]
            }
        }
    }

    fn apply_statuses(
        &mut self,
        result: Result<(Vec<ServiceStatus>, BTreeMap<String, String>), String>,
    ) -> Vec<Effect> {
        self.refreshing = false;
        let keep = self.selected_name();
        match result {
            Ok((rows, locked)) => {
                self.error.clear();
                self.rows = rows;
                self.locked = locked;
                if !self.manage_ready || !self.manage_dirty {
                    self.manage = self
                        .rows
                        .iter()
                        .filter(|r| r.running_count > 0 && !self.locked.contains_key(&r.name))
                        .map(|r| r.name.clone())
                        .collect();
                    self.manage_ready = true;
                }
                if !self.busy && self.log_target.is_none() {
                    self.status = format!("Loaded {} services", self.rows.len());
                }
            }
            Err(message) => {
                self.rows.clear();
                self.status = message.clone();
                self.push_ops(message.clone());
                self.error = message;
            }
        }
        if let Some(name) = keep {
            if let Some(i) = self.tree_rows().iter().position(|t| match t {
                TreeRow::Service { index } => self.rows.get(*index).is_some_and(|r| r.name == name),
                TreeRow::Group { .. } => false,
            }) {
                self.selected = i;
            }
        } else if let Some(i) = self
            .tree_rows()
            .iter()
            .position(|t| matches!(t, TreeRow::Service { .. }))
        {
            self.selected = i;
        }
        self.clamp();
        if std::mem::take(&mut self.refresh_again) {
            self.request_refresh()
        } else {
            vec![]
        }
    }
}

#[cfg(test)]
#[path = "app_tests.rs"]
mod tests;
