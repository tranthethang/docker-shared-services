//! Drawing. Reads `App` and never changes it.

use super::app::{App, Modal};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Cell, Clear, Paragraph, Row, Table, TableState, Wrap};
use ratatui::Frame;

pub const HELP: &str = "\
Keyboard controls

  ↑/↓ or j/k   Move selection
  /            Filter (Enter or Esc returns to the list)
  Enter        Show details and stop following logs
  l            Follow live logs, or stop following
  u            Up (start) the selected service
  d            Down the selected service (asks first)
  s            Stop the selected service
  r            Restart the selected service
  R            Refresh status (also automatic on Docker events)
  Space        Toggle the row in the manage selection
  a / c        Select all / clear the manage selection
  m            Apply the manage plan (asks first)
  ?            This help
  q            Quit";

fn state_style(state: &str) -> Style {
    match state {
        "running" => Style::new().fg(Color::Green),
        "partial" => Style::new().fg(Color::Yellow),
        "stopped" => Style::new().fg(Color::Red),
        _ => Style::new().add_modifier(Modifier::DIM),
    }
}

fn health_style(health: &str) -> Style {
    match health {
        "healthy" => Style::new().fg(Color::Green),
        "starting" => Style::new().fg(Color::Yellow),
        "unhealthy" => Style::new().fg(Color::Red).add_modifier(Modifier::BOLD),
        "none" => Style::new(),
        _ => Style::new().add_modifier(Modifier::DIM),
    }
}

fn table(app: &App) -> Table<'static> {
    let rows: Vec<Row> = app
        .visible()
        .iter()
        .map(|r| {
            let locked = app.locked.contains_key(&r.name);
            let (mark, name_style) = if locked {
                ("—", Style::new().add_modifier(Modifier::DIM))
            } else if app.manage.contains(&r.name) {
                ("✓", Style::new())
            } else {
                (" ", Style::new())
            };
            Row::new(vec![
                Cell::from(mark).style(Style::new().fg(Color::Green).add_modifier(Modifier::BOLD)),
                Cell::from(r.name.clone()).style(name_style),
                Cell::from(r.state).style(state_style(r.state)),
                Cell::from(r.health).style(health_style(r.health)),
                Cell::from(format!("{}/{}", r.running_count, r.container_count)),
            ])
        })
        .collect();
    let widths = [
        Constraint::Length(2),
        Constraint::Min(18),
        Constraint::Length(8),
        Constraint::Length(10),
        Constraint::Length(5),
    ];
    Table::new(rows, widths)
        .header(
            Row::new(["✓", "Service", "State", "Health", "Ctrs"])
                .style(Style::new().add_modifier(Modifier::BOLD)),
        )
        .row_highlight_style(Style::new().add_modifier(Modifier::REVERSED))
        .block(Block::new().borders(Borders::ALL).title(" Services "))
}

fn detail_lines(app: &App) -> Vec<Line<'static>> {
    if app.log_target.is_some() {
        return app.logs.iter().map(|l| Line::raw(l.clone())).collect();
    }
    let Some(row) = app.selected_row() else {
        return vec![Line::raw(
            if app.error.is_empty() {
                "No services match."
            } else {
                app.error.as_str()
            }
            .to_string(),
        )];
    };
    let mut lines = vec![Line::raw(format!("Service: {}", row.name))];
    if let Some(reason) = app.locked.get(&row.name) {
        lines.push(Line::raw(format!("Label only: {reason}")));
    }
    lines.push(Line::raw(format!(
        "State: {}  Health: {}",
        row.state, row.health
    )));
    lines.push(Line::raw(format!(
        "Containers: {}/{}",
        row.running_count, row.container_count
    )));
    if row.containers.is_empty() {
        lines.push(Line::raw("(no containers — stack absent)"));
    }
    for c in &row.containers {
        lines.push(Line::raw(format!(
            "- {}  [{}]  {}/{}  {}",
            c.name, c.compose_service, c.status, c.health, c.image
        )));
    }
    lines
}

/// Show the last lines that fit, so the newest output stays visible.
fn tail(lines: Vec<Line<'static>>, height: u16) -> Vec<Line<'static>> {
    let keep = usize::from(height.saturating_sub(2));
    let skip = lines.len().saturating_sub(keep);
    lines.into_iter().skip(skip).collect()
}

fn panel(title: String, lines: Vec<Line<'static>>, area: Rect) -> Paragraph<'static> {
    Paragraph::new(tail(lines, area.height))
        .wrap(Wrap { trim: false })
        .block(Block::new().borders(Borders::ALL).title(title))
}

fn centered(area: Rect, width: u16, height: u16) -> Rect {
    let (w, h) = (width.min(area.width), height.min(area.height));
    Rect::new(
        area.x + (area.width - w) / 2,
        area.y + (area.height - h) / 2,
        w,
        h,
    )
}

fn modal(frame: &mut Frame, modal: &Modal) {
    let (title, body, hint) = match modal {
        Modal::Help => ("Help".to_string(), HELP.to_string(), "Esc closes"),
        Modal::Confirm { title, body, .. } => {
            (title.clone(), body.clone(), "y confirms · n or Esc cancels")
        }
    };
    let lines = body.lines().count() as u16 + 4;
    let width = body
        .lines()
        .map(|l| l.chars().count() as u16)
        .max()
        .unwrap_or(0)
        .max(40)
        + 4;
    let area = centered(frame.area(), width, lines);
    frame.render_widget(Clear, area);
    let block = Block::new()
        .borders(Borders::ALL)
        .title(format!(" {title} "))
        .title_bottom(format!(" {hint} "))
        .border_style(Style::new().fg(Color::Cyan));
    frame.render_widget(
        Paragraph::new(body).wrap(Wrap { trim: false }).block(block),
        area,
    );
}

pub fn draw(frame: &mut Frame, app: &App) {
    let outer = Layout::vertical([
        Constraint::Length(1),
        Constraint::Length(1),
        Constraint::Min(5),
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .split(frame.area());
    frame.render_widget(
        Paragraph::new(Span::styled(
            " Docker Shared Services",
            Style::new().add_modifier(Modifier::BOLD),
        )),
        outer[0],
    );
    let filter = if app.filter_mode {
        format!(" /{}█", app.filter)
    } else if app.filter.is_empty() {
        " / to filter".to_string()
    } else {
        format!(" /{}", app.filter)
    };
    frame.render_widget(
        Paragraph::new(filter).style(Style::new().add_modifier(Modifier::DIM)),
        outer[1],
    );
    let main = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(42), Constraint::Percentage(58)])
        .split(outer[2]);
    let mut state = TableState::default().with_selected(Some(app.selected));
    frame.render_stateful_widget(table(app), main[0], &mut state);
    let side =
        Layout::vertical([Constraint::Percentage(60), Constraint::Percentage(40)]).split(main[1]);
    let title = match (&app.log_target, app.selected_row()) {
        (Some(t), _) => format!(" Logs · {t} "),
        (None, Some(r)) => format!(" Details · {} ", r.name),
        (None, None) => " Details ".into(),
    };
    frame.render_widget(panel(title, detail_lines(app), side[0]), side[0]);
    let ops = app.ops.iter().map(|l| Line::raw(l.clone())).collect();
    frame.render_widget(panel(" Operations ".into(), ops, side[1]), side[1]);
    let busy = if app.busy { " ⏳" } else { "" };
    frame.render_widget(
        Paragraph::new(format!(" {}{busy}", app.status))
            .style(Style::new().add_modifier(Modifier::DIM)),
        outer[3],
    );
    let keys = " q quit · ? help · / filter · u up · d down · s stop · r restart · l logs · space select · m manage";
    frame.render_widget(
        Paragraph::new(keys).style(Style::new().add_modifier(Modifier::REVERSED)),
        outer[4],
    );
    if let Some(m) = &app.modal {
        modal(frame, m);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    fn render(app: &App) -> String {
        let mut terminal = Terminal::new(TestBackend::new(100, 24)).unwrap();
        terminal.draw(|f| draw(f, app)).unwrap();
        terminal
            .backend()
            .buffer()
            .content()
            .iter()
            .map(|c| c.symbol())
            .collect()
    }

    #[test]
    fn draws_the_empty_dashboard_without_a_terminal() {
        let text = render(&App::new());
        assert!(
            text.contains("Docker Shared Services")
                && text.contains("Services")
                && text.contains("Operations")
        );
    }

    #[test]
    fn help_modal_lists_the_keys() {
        let mut app = App::new();
        app.modal = Some(Modal::Help);
        let text = render(&app);
        assert!(text.contains("Keyboard controls") && text.contains("Apply the manage plan"));
    }

    #[test]
    fn tail_keeps_the_newest_lines() {
        let lines: Vec<Line> = (0..10).map(|i| Line::raw(i.to_string())).collect();
        let kept = tail(lines, 5);
        assert_eq!(kept.len(), 3);
        assert_eq!(kept[2].to_string(), "9");
    }
}
