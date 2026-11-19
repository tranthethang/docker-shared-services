//! ratatui wizard: pick services, name the stack, and export.

use super::{partition_selection, validate_stack_name};
use crate::config::{active_services, PACKAGE_DEFAULT_SERVICES};
use crossterm::event::{KeyCode, KeyEvent, KeyModifiers};
use std::collections::BTreeSet;
use std::path::Path;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Step {
    Select,
    Name,
    Confirm,
}

#[derive(PartialEq, Eq, Debug)]
pub enum Outcome {
    Continue,
    Cancel,
    /// The user confirmed: export these services under this name.
    Export(Vec<String>, String),
}

pub struct Wizard {
    pub step: Step,
    pub items: Vec<&'static str>,
    pub checked: BTreeSet<&'static str>,
    pub cursor: usize,
    pub name: String,
    pub error: String,
}

impl Wizard {
    pub fn new() -> Self {
        let items = active_services().to_vec();
        let checked = items
            .iter()
            .copied()
            .filter(|s| PACKAGE_DEFAULT_SERVICES.contains(s))
            .collect();
        Self {
            step: Step::Select,
            items,
            checked,
            cursor: 0,
            name: String::new(),
            error: String::new(),
        }
    }

    pub fn selected(&self) -> Vec<String> {
        self.items
            .iter()
            .filter(|s| self.checked.contains(*s))
            .map(|s| s.to_string())
            .collect()
    }

    /// `(checked, added dependencies)` for the current selection.
    pub fn plan(&self, root: &Path) -> Result<(Vec<String>, Vec<String>), String> {
        partition_selection(&self.selected(), root)
    }

    pub fn on_key(&mut self, key: KeyEvent, root: &Path) -> Outcome {
        if key.modifiers.contains(KeyModifiers::CONTROL) && key.code == KeyCode::Char('c') {
            return Outcome::Cancel;
        }
        match self.step {
            Step::Select => self.select_key(key.code),
            Step::Name => self.name_key(key.code),
            Step::Confirm => self.confirm_key(key.code, root),
        }
    }

    fn select_key(&mut self, code: KeyCode) -> Outcome {
        let last = self.items.len().saturating_sub(1);
        match code {
            KeyCode::Char('q') | KeyCode::Esc => return Outcome::Cancel,
            KeyCode::Char('j') | KeyCode::Down => self.cursor = (self.cursor + 1).min(last),
            KeyCode::Char('k') | KeyCode::Up => self.cursor = self.cursor.saturating_sub(1),
            KeyCode::Char(' ') => {
                let name = self.items[self.cursor];
                if !self.checked.remove(name) {
                    self.checked.insert(name);
                }
            }
            KeyCode::Char('a') => self.checked = self.items.iter().copied().collect(),
            KeyCode::Char('c') => self.checked.clear(),
            KeyCode::Enter if self.checked.is_empty() => {
                self.error = "Select at least one service.".into()
            }
            KeyCode::Enter => {
                self.error.clear();
                self.step = Step::Name;
            }
            _ => {}
        }
        Outcome::Continue
    }

    fn name_key(&mut self, code: KeyCode) -> Outcome {
        match code {
            KeyCode::Esc => self.step = Step::Select,
            KeyCode::Backspace => {
                self.name.pop();
            }
            KeyCode::Char(c) => self.name.push(c),
            KeyCode::Enter => match validate_stack_name(&self.name) {
                Ok(_) => {
                    self.error.clear();
                    self.step = Step::Confirm;
                }
                Err(e) => self.error = e,
            },
            _ => {}
        }
        Outcome::Continue
    }

    fn confirm_key(&mut self, code: KeyCode, root: &Path) -> Outcome {
        match code {
            KeyCode::Char('n') | KeyCode::Esc => self.step = Step::Name,
            KeyCode::Char('y') | KeyCode::Enter => match self.plan(root) {
                Ok((checked, added)) => {
                    return Outcome::Export([checked, added].concat(), self.name.clone())
                }
                Err(e) => self.error = e,
            },
            _ => {}
        }
        Outcome::Continue
    }
}

#[cfg(test)]
#[path = "wizard_tests.rs"]
mod tests;
