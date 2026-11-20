//! Key handling for the dashboard.

use super::app::{App, Effect, Modal, OpKind, Plan};
use super::presets;
use super::tree::{self, TreeRow};
use crate::docker::{shutdown_queue, startup_queue};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};

impl App {
    pub fn on_key(&mut self, key: KeyEvent) -> Vec<Effect> {
        if let Some(modal) = self.modal.clone() {
            return self.modal_key(modal, key);
        }
        if self.filter_mode {
            self.filter_key(key);
            return vec![];
        }
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            return vec![Effect::Quit];
        }
        match key.code {
            KeyCode::Char('q') => vec![Effect::Quit],
            KeyCode::Char('?') => self.open(Modal::Help),
            KeyCode::Char('/') => {
                self.filter_mode = true;
                vec![]
            }
            KeyCode::Char('j') | KeyCode::Down => self.step(1),
            KeyCode::Char('k') | KeyCode::Up => self.step(-1),
            KeyCode::Left => {
                tree::set_group_collapsed(self, true);
                vec![]
            }
            KeyCode::Right => {
                tree::set_group_collapsed(self, false);
                vec![]
            }
            KeyCode::Enter => self.on_enter(),
            KeyCode::Char('o') => self.open_web_ui(),
            KeyCode::Char('f') => self.toggle_active_only(),
            KeyCode::Char('z') => self.toggle_zoom(),
            KeyCode::Char('p') => self.open(Modal::Presets { selected: 0 }),
            KeyCode::Char('l') => self.toggle_logs(),
            KeyCode::Char('R') => self.refresh_now(),
            KeyCode::Char('u') => self.single(OpKind::Up),
            KeyCode::Char('d') => self.single(OpKind::Down),
            KeyCode::Char('s') => self.single(OpKind::Stop),
            KeyCode::Char('r') => self.single(OpKind::Restart),
            KeyCode::Char(' ') => self.toggle_manage(),
            KeyCode::Char('a') => self.select_all(),
            KeyCode::Char('c') => self.clear_manage(),
            KeyCode::Char('m') => self.manage_plan(),
            _ => vec![],
        }
    }

    fn open(&mut self, modal: Modal) -> Vec<Effect> {
        self.modal = Some(modal);
        vec![]
    }

    fn modal_key(&mut self, modal: Modal, key: KeyEvent) -> Vec<Effect> {
        let confirm = matches!(modal, Modal::Confirm { .. });
        match (key.code, modal) {
            (KeyCode::Char('y'), Modal::Confirm { plan, .. }) => {
                self.modal = None;
                self.busy = true;
                self.status = "Working…".into();
                vec![Effect::Run(plan)]
            }
            (KeyCode::Char('n') | KeyCode::Esc, _) if confirm => {
                self.modal = None;
                self.status = "Cancelled".into();
                vec![]
            }
            (KeyCode::Esc | KeyCode::Char('q') | KeyCode::Enter, Modal::Help) => {
                self.modal = None;
                vec![]
            }
            (code, Modal::Presets { selected }) => {
                presets::handle_key(self, selected, code);
                vec![]
            }
            _ => vec![],
        }
    }

    fn filter_key(&mut self, key: KeyEvent) {
        match key.code {
            KeyCode::Enter | KeyCode::Esc => self.filter_mode = false,
            KeyCode::Backspace => {
                self.filter.pop();
            }
            KeyCode::Char(c) => self.filter.push(c),
            _ => {}
        }
        self.clamp();
    }

    fn step(&mut self, delta: isize) -> Vec<Effect> {
        let last = self.tree_rows().len().saturating_sub(1);
        self.selected = self.selected.saturating_add_signed(delta).min(last);
        vec![]
    }

    fn on_enter(&mut self) -> Vec<Effect> {
        if let Some(TreeRow::Group {
            category,
            collapsed,
            ..
        }) = self.selected_tree_row()
        {
            tree::fold_category(self, category, !collapsed);
            return vec![];
        }
        self.stop_logs()
    }

    fn open_web_ui(&mut self) -> Vec<Effect> {
        let Some(row) = self.selected_row() else {
            self.status = "No service selected".into();
            return vec![];
        };
        if let Some(url) = self.catalog.get(&row.name).and_then(|e| e.web_ui.first()) {
            self.status = format!("Opening {url}");
            return vec![Effect::OpenUrl(url.clone())];
        }
        self.status = format!("No Web UI URL configured for {}", row.name);
        vec![]
    }

    fn toggle_active_only(&mut self) -> Vec<Effect> {
        self.active_only = !self.active_only;
        self.clamp();
        self.status = if self.active_only {
            "Showing active services only"
        } else {
            "Showing all services"
        }
        .into();
        vec![]
    }

    fn toggle_zoom(&mut self) -> Vec<Effect> {
        self.zoom_details = !self.zoom_details;
        vec![]
    }

    fn stop_logs(&mut self) -> Vec<Effect> {
        if self.log_target.take().is_some() {
            self.logs.clear();
            return vec![Effect::StopLogs];
        }
        vec![]
    }

    fn toggle_logs(&mut self) -> Vec<Effect> {
        if self.log_target.is_some() {
            return self.stop_logs();
        }
        let Some(row) = self.selected_row() else {
            return vec![];
        };
        if row.containers.is_empty() {
            self.status = format!("{} has no containers", row.name);
            return vec![];
        }
        let (name, containers) = (row.name.clone(), row.containers.clone());
        self.status = format!("Following logs for {name}");
        self.log_target = Some(name);
        self.logs.clear();
        vec![Effect::FollowLogs(containers)]
    }

    fn refresh_now(&mut self) -> Vec<Effect> {
        if self.busy {
            self.status = "Busy — wait for the current operation".into();
            return vec![];
        }
        self.request_refresh()
    }

    fn single(&mut self, kind: OpKind) -> Vec<Effect> {
        let Some(name) = self.selected_name() else {
            return vec![];
        };
        if self.busy {
            self.status = "Busy — wait for the current operation".into();
            return vec![];
        }
        if matches!(kind, OpKind::Up | OpKind::Restart) {
            if let Some(reason) = self.locked.get(&name) {
                self.status = format!("{name} is label only: {reason}");
                return vec![];
            }
        }
        let plan = Plan::Single(name.clone(), kind);
        if kind == OpKind::Down {
            let body = format!("Stop and remove the containers of {name}?");
            return self.open(Modal::Confirm {
                title: format!("Down {name}"),
                body,
                plan,
            });
        }
        self.busy = true;
        self.status = format!("Working on {name}…");
        vec![Effect::Run(plan)]
    }

    fn toggle_manage(&mut self) -> Vec<Effect> {
        let Some(name) = self.selected_name() else {
            return vec![];
        };
        if let Some(reason) = self.locked.get(&name) {
            self.status = format!("{name} is label only: {reason}");
            return vec![];
        }
        if !self.manage.remove(&name) {
            self.manage.insert(name);
        }
        self.manage_dirty = true;
        self.status = format!("Manage selection: {} service(s)", self.manage.len());
        vec![]
    }

    fn select_all(&mut self) -> Vec<Effect> {
        self.manage = self
            .visible()
            .iter()
            .filter(|r| !self.locked.contains_key(&r.name))
            .map(|r| r.name.clone())
            .collect();
        self.manage_dirty = true;
        vec![]
    }

    fn clear_manage(&mut self) -> Vec<Effect> {
        self.manage.clear();
        self.manage_dirty = true;
        vec![]
    }

    /// Start the selected services that are down, and stop the running ones that are not selected.
    pub fn manage_changes(&self) -> (Vec<String>, Vec<String>) {
        let running: Vec<String> = self
            .rows
            .iter()
            .filter(|r| r.running_count > 0 && !self.locked.contains_key(&r.name))
            .map(|r| r.name.clone())
            .collect();
        let up: Vec<String> = self
            .manage
            .iter()
            .filter(|n| !running.contains(n))
            .cloned()
            .collect();
        let down: Vec<String> = running
            .into_iter()
            .filter(|n| !self.manage.contains(n))
            .collect();
        (startup_queue(&up), shutdown_queue(&down))
    }

    fn manage_plan(&mut self) -> Vec<Effect> {
        if self.busy {
            self.status = "Busy — wait for the current operation".into();
            return vec![];
        }
        let (up, down) = self.manage_changes();
        if up.is_empty() && down.is_empty() {
            self.status = "No changes needed".into();
            return vec![];
        }
        let mut body = String::new();
        if !up.is_empty() {
            body.push_str(&format!("Will start: {}\n", up.join(", ")));
        }
        if !down.is_empty() {
            body.push_str(&format!("Will stop:  {}\n", down.join(", ")));
        }
        self.open(Modal::Confirm {
            title: "Apply manage plan".into(),
            body,
            plan: Plan::Manage { up, down },
        })
    }
}
