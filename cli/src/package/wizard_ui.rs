//! Drawing and the event loop of the package wizard.

use super::export_stack;
use super::wizard::{Outcome, Step, Wizard};
use crate::tui::TerminalGuard;
use crossterm::event::{self, Event, KeyEventKind};
use ratatui::backend::CrosstermBackend;
use ratatui::layout::Constraint;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::Line;
use ratatui::widgets::{Block, Borders, List, ListItem, ListState, Paragraph, Wrap};
use ratatui::{Frame, Terminal};
use std::io::{stdout, IsTerminal};
use std::path::{Path, PathBuf};
use std::time::Duration;

fn hint(step: Step) -> &'static str {
    match step {
        Step::Select => " space toggle · a all · c clear · Enter next · q cancel",
        Step::Name => " type a name · Enter next · Esc back",
        Step::Confirm => " y or Enter export · n or Esc back",
    }
}

fn select_list(w: &Wizard, root: &Path) -> List<'static> {
    let added = w.plan(root).map(|(_, added)| added).unwrap_or_default();
    let items: Vec<ListItem> = w
        .items
        .iter()
        .map(|s| {
            let mark = if w.checked.contains(s) { "[x]" } else { "[ ]" };
            let extra = if added.iter().any(|a| a == s) && !w.checked.contains(s) {
                "  (added: dependency)"
            } else {
                ""
            };
            ListItem::new(format!(" {mark} {s}{extra}"))
        })
        .collect();
    List::new(items)
        .highlight_style(Style::new().add_modifier(Modifier::REVERSED))
        .block(
            Block::new()
                .borders(Borders::ALL)
                .title(" Select services "),
        )
}

fn summary(w: &Wizard, root: &Path) -> Vec<Line<'static>> {
    let mut lines = vec![
        Line::raw(format!("Stack name: {}", w.name)),
        Line::raw(format!("Destination: dist/{}", w.name)),
        Line::raw(""),
    ];
    match w.plan(root) {
        Ok((checked, added)) => {
            lines.push(Line::raw(format!("Services: {}", checked.join(", "))));
            if !added.is_empty() {
                lines.push(Line::raw(format!(
                    "Added dependencies: {}",
                    added.join(", ")
                )));
            }
        }
        Err(e) => lines.push(Line::raw(e)),
    }
    lines
}

pub fn draw(frame: &mut Frame, w: &Wizard, root: &Path) {
    let rows = ratatui::layout::Layout::vertical([
        Constraint::Length(1),
        Constraint::Min(5),
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .split(frame.area());
    frame.render_widget(
        Paragraph::new(" Package a stack").style(Style::new().add_modifier(Modifier::BOLD)),
        rows[0],
    );
    match w.step {
        Step::Select => {
            let mut state = ListState::default().with_selected(Some(w.cursor));
            frame.render_stateful_widget(select_list(w, root), rows[1], &mut state);
        }
        Step::Name => {
            let text = format!(
                "Stack name (lowercase letters, digits, dashes):\n\n> {}█",
                w.name
            );
            frame.render_widget(
                Paragraph::new(text).block(Block::new().borders(Borders::ALL).title(" Name ")),
                rows[1],
            );
        }
        Step::Confirm => {
            let block = Block::new().borders(Borders::ALL).title(" Confirm ");
            frame.render_widget(
                Paragraph::new(summary(w, root))
                    .wrap(Wrap { trim: false })
                    .block(block),
                rows[1],
            );
        }
    }
    frame.render_widget(
        Paragraph::new(format!(" {}", w.error)).style(Style::new().fg(Color::Red)),
        rows[2],
    );
    frame.render_widget(
        Paragraph::new(hint(w.step)).style(Style::new().add_modifier(Modifier::REVERSED)),
        rows[3],
    );
}

/// Run the wizard. Returns the exported path, or `None` when cancelled.
pub fn run(root: &Path) -> Result<Option<PathBuf>, String> {
    if !stdout().is_terminal() || !std::io::stdin().is_terminal() {
        return Err("the wizard needs an interactive terminal. Use `dss package --name <n> --services <a,b>`.".into());
    }
    let mut wizard = Wizard::new();
    let outcome = {
        let _guard = TerminalGuard::enter()?;
        let mut terminal =
            Terminal::new(CrosstermBackend::new(stdout())).map_err(|e| e.to_string())?;
        loop {
            terminal
                .draw(|f| draw(f, &wizard, root))
                .map_err(|e| e.to_string())?;
            if !event::poll(Duration::from_millis(100)).map_err(|e| e.to_string())? {
                continue;
            }
            let Event::Key(key) = event::read().map_err(|e| e.to_string())? else {
                continue;
            };
            if key.kind != KeyEventKind::Press {
                continue;
            }
            match wizard.on_key(key, root) {
                Outcome::Continue => {}
                done => break done,
            }
        }
    };
    match outcome {
        Outcome::Export(services, name) => export_stack(&services, &name, root, None).map(Some),
        _ => Ok(None),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;

    fn render(w: &Wizard) -> String {
        let root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        let mut terminal = Terminal::new(TestBackend::new(90, 24)).unwrap();
        terminal.draw(|f| draw(f, w, root)).unwrap();
        terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|c| c.symbol())
            .collect()
    }

    #[test]
    fn draws_each_step_without_a_terminal() {
        let mut w = Wizard::new();
        assert!(render(&w).contains("Select services"));
        w.step = Step::Name;
        w.name = "demo".into();
        assert!(render(&w).contains("Stack name"));
        w.step = Step::Confirm;
        let text = render(&w);
        assert!(text.contains("Confirm") && text.contains("dist/demo"));
    }
}
