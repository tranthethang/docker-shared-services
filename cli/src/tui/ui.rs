//! Drawing. Reads `App` and never changes it.

use super::app::App;
use super::theme::Theme;
use super::tree::services_table;
use super::widgets::{
    format_bytes, health_style, keycap_line, render_modal, rounded_block, state_dot, telemetry_bar,
};
use ratatui::layout::{Constraint, Direction, Layout, Rect};
use ratatui::style::{Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Paragraph, TableState, Wrap};
use ratatui::Frame;

pub const HELP: &str = "\
Keyboard controls

  ↑/↓ or j/k   Move selection
  ←/→ or Enter Fold / unfold category group
  /            Filter (Enter or Esc returns to the list)
  f            Toggle active services only
  z            Zoom Details / Logs panel
  o            Open Web UI URL in browser
  p            Stack Presets picker
  Enter        Show details and stop following logs
  l            Follow live logs, or stop following
  u / d / s / r Up / Down / Stop / Restart selected service
  R            Refresh status (also automatic on Docker events)
  Space        Toggle the row in the manage selection
  a / c        Select all / clear the manage selection
  m            Apply the manage plan (asks first)
  ? / q        This help / Quit";

fn detail_lines(app: &App) -> Vec<Line<'static>> {
    let t = &app.theme;
    if app.log_target.is_some() {
        return app.logs.iter().map(|l| Line::raw(l.clone())).collect();
    }
    let Some(row) = app.selected_row() else {
        let msg = if app.error.is_empty() {
            "Select a service or group."
        } else {
            app.error.as_str()
        };
        return vec![Line::styled(msg.to_string(), Style::new().fg(t.text_muted))];
    };
    let mut lines = Vec::new();
    if let Some(entry) = app.catalog.get(&row.name) {
        lines.push(Line::from(vec![
            Span::styled(
                format!("[{}] ", entry.category),
                Style::new().fg(t.border_focus).add_modifier(Modifier::BOLD),
            ),
            Span::styled(entry.description.clone(), Style::new().fg(t.text_primary)),
        ]));
        for url in &entry.web_ui {
            lines.push(Line::from(vec![
                Span::styled("Web UI: ", Style::new().fg(t.text_muted)),
                Span::styled(url.clone(), Style::new().fg(t.green)),
            ]));
        }
    }
    if let Some(reason) = app.locked.get(&row.name) {
        lines.push(Line::styled(
            format!("Label only: {reason}"),
            Style::new().fg(t.amber),
        ));
    }
    lines.push(Line::from(vec![
        Span::styled("State: ", Style::new().fg(t.text_muted)),
        Span::styled(row.state, state_dot(row.state, t).1),
        Span::styled("  Health: ", Style::new().fg(t.text_muted)),
        Span::styled(row.health, health_style(row.health, t)),
        Span::styled(
            format!(
                "  Containers: {}/{}",
                row.running_count, row.container_count
            ),
            Style::new().fg(t.text_muted),
        ),
    ]));
    if row.containers.is_empty() {
        lines.push(Line::styled(
            "(no containers — stack absent)",
            Style::new().fg(t.text_muted),
        ));
    } else {
        lines.push(Line::styled(
            "Container                 CPU    MEM     Image",
            Style::new().fg(t.text_muted).add_modifier(Modifier::BOLD),
        ));
        for c in &row.containers {
            let (cpu, mem) = app
                .stats
                .get(&c.name)
                .map(|s| {
                    (
                        format!("{:4.1}%", s.cpu_pct),
                        format_bytes(s.mem_used_bytes),
                    )
                })
                .unwrap_or_else(|| ("  —  ".into(), "—".into()));
            lines.push(Line::raw(format!(
                "{:<24} {:>5}  {:>6}  {}",
                c.name, cpu, mem, c.image
            )));
        }
    }
    lines
}

/// Show the last lines that fit, so the newest output stays visible.
fn tail(lines: Vec<Line<'static>>, height: u16) -> Vec<Line<'static>> {
    let keep = usize::from(height.saturating_sub(2));
    let skip = lines.len().saturating_sub(keep);
    lines.into_iter().skip(skip).collect()
}

fn panel(
    title: String,
    lines: Vec<Line<'static>>,
    area: Rect,
    theme: &Theme,
) -> Paragraph<'static> {
    Paragraph::new(tail(lines, area.height))
        .wrap(Wrap { trim: false })
        .block(rounded_block(title, false, theme))
}

pub fn draw(frame: &mut Frame, app: &App) {
    let t = &app.theme;
    let outer = Layout::vertical([
        Constraint::Length(3),
        Constraint::Length(1),
        Constraint::Min(5),
        Constraint::Length(1),
        Constraint::Length(1),
    ])
    .split(frame.area());
    frame.render_widget(telemetry_bar(app), outer[0]);
    let active_tag = if app.active_only {
        " [active only]"
    } else {
        ""
    };
    let filter = if app.filter_mode {
        format!(" /{}█{active_tag}", app.filter)
    } else if app.filter.is_empty() {
        format!(" / to filter{active_tag}")
    } else {
        format!(" /{}{active_tag}", app.filter)
    };
    frame.render_widget(
        Paragraph::new(filter).style(Style::new().fg(t.text_muted)),
        outer[1],
    );
    let ops_constraint = if app.busy {
        Constraint::Percentage(38)
    } else {
        Constraint::Length(5)
    };
    let side_area = if app.zoom_details {
        outer[2]
    } else {
        let main = Layout::default()
            .direction(Direction::Horizontal)
            .constraints([Constraint::Percentage(44), Constraint::Percentage(56)])
            .split(outer[2]);
        let mut state = TableState::default().with_selected(Some(app.selected));
        frame.render_stateful_widget(services_table(app), main[0], &mut state);
        main[1]
    };
    let side = Layout::vertical([Constraint::Min(5), ops_constraint]).split(side_area);
    let title = match (&app.log_target, app.selected_row()) {
        (Some(target), _) => format!(" Logs · {target} "),
        (None, Some(r)) => format!(" Details · {} ", r.name),
        (None, None) => " Details ".into(),
    };
    frame.render_widget(panel(title, detail_lines(app), side[0], t), side[0]);
    let ops = app.ops.iter().map(|l| Line::raw(l.clone())).collect();
    frame.render_widget(panel(" Operations ".into(), ops, side[1], t), side[1]);
    let busy = if app.busy { " ⏳" } else { "" };
    frame.render_widget(
        Paragraph::new(format!(" {}{busy}", app.status)).style(Style::new().fg(t.text_muted)),
        outer[3],
    );
    let footer = keycap_line(
        &[
            ("q", "Quit"),
            ("?", "Help"),
            ("/", "Filter"),
            ("f", "Active"),
            ("z", "Zoom"),
            ("o", "Open"),
            ("p", "Presets"),
            ("u", "Up"),
            ("d", "Down"),
            ("s", "Stop"),
            ("l", "Logs"),
            ("m", "Manage"),
        ],
        t,
    );
    frame.render_widget(
        Paragraph::new(footer).style(Style::new().bg(t.surface_elevated)),
        outer[4],
    );
    if let Some(m) = &app.modal {
        render_modal(frame, m, HELP, t);
    }
}

#[cfg(test)]
mod tests {
    use super::super::app::Modal;
    use super::*;
    use ratatui::backend::TestBackend;
    use ratatui::Terminal;

    fn render(app: &App, width: u16, height: u16) -> String {
        let mut terminal = Terminal::new(TestBackend::new(width, height)).unwrap();
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
        for (w, h) in [(120, 36), (100, 24)] {
            let text = render(&App::new(), w, h);
            assert!(
                text.contains("Docker Shared Services")
                    && text.contains("Services")
                    && text.contains("Operations")
            );
        }
    }

    #[test]
    fn draws_telemetry_presets_and_zoom() {
        let mut app = App::new();
        app.on_msg(super::super::app::Msg::Capacity(
            crate::docker::stats::DockerCapacity {
                ncpu: 4,
                mem_total_bytes: 8 * 1024 * 1024 * 1024,
            },
        ));
        app.zoom_details = true;
        let zoomed = render(&app, 120, 36);
        assert!(zoomed.contains("8.0G") && !zoomed.contains("MEM / CPU"));
        app.modal = Some(Modal::Presets { selected: 0 });
        let modal_text = render(&app, 120, 36);
        assert!(modal_text.contains("Stack Presets") && modal_text.contains("Core Infra"));
    }

    #[test]
    fn help_modal_lists_the_keys() {
        let mut app = App::new();
        app.modal = Some(Modal::Help);
        let text = render(&app, 100, 24);
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
