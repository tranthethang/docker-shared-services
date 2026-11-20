//! Reusable TUI widgets and formatting helpers.

use super::app::{App, Modal};
use super::presets::{available_services, PRESETS};
use super::theme::Theme;
use ratatui::layout::Rect;
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, BorderType, Borders, Clear, Paragraph, Wrap};
use ratatui::Frame;
use std::collections::VecDeque;

const GAUGE_BLOCKS: [char; 8] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█'];
const SPARK_BLOCKS: [char; 8] = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

/// Threshold coloring: `<65%` green, `65–85%` amber, `>85%` red.
pub fn threshold_color(pct: f64, theme: &Theme) -> Color {
    if pct > 85.0 {
        theme.red
    } else if pct >= 65.0 {
        theme.amber
    } else {
        theme.green
    }
}

/// Render a Unicode sub-character progress bar of `width` cells.
pub fn gauge_bar(pct: f64, width: usize) -> String {
    if width == 0 {
        return String::new();
    }
    let clamped = pct.clamp(0.0, 100.0);
    let eighths = ((clamped / 100.0) * (width * 8) as f64).round() as usize;
    let full = eighths / 8;
    let rem = eighths % 8;
    let mut out = String::with_capacity(width);
    for _ in 0..full.min(width) {
        out.push('█');
    }
    if full < width {
        if rem > 0 {
            out.push(GAUGE_BLOCKS[rem - 1]);
        } else {
            out.push('░');
        }
        for _ in (full + 1)..width {
            out.push('░');
        }
    }
    out
}

/// Render a Unicode sparkline (`▁`–`█`) from recent CPU samples.
pub fn sparkline(samples: &VecDeque<f64>, width: usize) -> String {
    if width == 0 {
        return String::new();
    }
    let max_val = samples.iter().copied().fold(10.0_f64, f64::max).max(1.0);
    let start = samples.len().saturating_sub(width);
    let pad = width.saturating_sub(samples.len());
    let mut out = String::with_capacity(width);
    for _ in 0..pad {
        out.push(SPARK_BLOCKS[0]);
    }
    for &v in samples.iter().skip(start) {
        let ratio = (v.max(0.0) / max_val).clamp(0.0, 1.0);
        let idx = ((ratio * 7.0).round() as usize).min(7);
        out.push(SPARK_BLOCKS[idx]);
    }
    out
}

/// Format bytes into compact human-readable units (`42M`, `3.2G`, `512K`, `0B`).
pub fn format_bytes(bytes: u64) -> String {
    const KIB: f64 = 1024.0;
    const MIB: f64 = KIB * 1024.0;
    const GIB: f64 = MIB * 1024.0;
    let b = bytes as f64;
    if b >= GIB {
        format!("{:.1}G", b / GIB)
    } else if b >= MIB {
        format!("{:.0}M", b / MIB)
    } else if b >= KIB {
        format!("{:.0}K", b / KIB)
    } else {
        format!("{bytes}B")
    }
}

/// Rounded bordered block styled with the active `Theme`.
pub fn rounded_block<'a>(title: impl Into<Line<'a>>, focused: bool, theme: &Theme) -> Block<'a> {
    let border_color = if focused {
        theme.border_focus
    } else {
        theme.border_muted
    };
    Block::new()
        .borders(Borders::ALL)
        .border_type(BorderType::Rounded)
        .border_style(Style::new().fg(border_color))
        .style(Style::new().bg(theme.surface_base).fg(theme.text_primary))
        .title(title)
}

/// Render a compact keycap footer line (`[u] Up  [d] Down ...`).
pub fn keycap_line(pairs: &[(&str, &str)], theme: &Theme) -> Line<'static> {
    let mut spans = Vec::with_capacity(pairs.len() * 2 + 1);
    spans.push(Span::raw(" "));
    for (idx, (key, label)) in pairs.iter().enumerate() {
        if idx > 0 {
            spans.push(Span::styled("  ", Style::new().fg(theme.text_muted)));
        }
        spans.push(Span::styled(
            format!("[{key}]"),
            Style::new()
                .fg(theme.border_focus)
                .add_modifier(Modifier::BOLD),
        ));
        spans.push(Span::styled(
            format!(" {label}"),
            Style::new().fg(theme.text_muted),
        ));
    }
    Line::from(spans)
}

/// Center a modal rectangle inside `area`.
pub fn centered(area: Rect, width: u16, height: u16) -> Rect {
    let (w, h) = (width.min(area.width), height.min(area.height));
    Rect::new(
        area.x + (area.width - w) / 2,
        area.y + (area.height - h) / 2,
        w,
        h,
    )
}

/// Status dot symbol and style for a service state.
pub fn state_dot(state: &str, theme: &Theme) -> (&'static str, Style) {
    match state {
        "running" => ("●", Style::new().fg(theme.green)),
        "partial" => ("◐", Style::new().fg(theme.amber)),
        "stopped" => ("✕", Style::new().fg(theme.red)),
        _ => ("○", Style::new().fg(theme.text_muted)),
    }
}

/// Style for a service health string.
pub fn health_style(health: &str, theme: &Theme) -> Style {
    match health {
        "healthy" => Style::new().fg(theme.green),
        "starting" => Style::new().fg(theme.amber),
        "unhealthy" => Style::new().fg(theme.red).add_modifier(Modifier::BOLD),
        _ => Style::new().fg(theme.text_muted),
    }
}

/// Render the 3-line top Telemetry Bar.
pub fn telemetry_bar(app: &App) -> Paragraph<'static> {
    let t = &app.theme;
    let running = app.rows.iter().filter(|r| r.running_count > 0).count();
    let total = app.rows.len();
    let healthy = app.rows.iter().filter(|r| r.health == "healthy").count();
    let unhealthy = app.rows.iter().filter(|r| r.health == "unhealthy").count();
    let (cpu_pct, mem_used) = app.total_usage();
    let cpu_norm = app
        .capacity
        .filter(|c| c.ncpu > 0)
        .map(|c| cpu_pct / f64::from(c.ncpu))
        .unwrap_or(cpu_pct);
    let (ram_label, ram_pct) = match app.capacity.filter(|c| c.mem_total_bytes > 0) {
        Some(cap) => (
            format!(
                "{}/{}",
                format_bytes(mem_used),
                format_bytes(cap.mem_total_bytes)
            ),
            (mem_used as f64 / cap.mem_total_bytes as f64) * 100.0,
        ),
        None => (format_bytes(mem_used), 0.0),
    };
    let disk = app
        .disk_usage
        .map(|d| {
            format!(
                "{} ({} free)",
                format_bytes(d.total_bytes),
                format_bytes(d.reclaimable_bytes)
            )
        })
        .unwrap_or_else(|| "—".into());
    let domain = if app.domain.is_empty() {
        "sandbox.localhost"
    } else {
        &app.domain
    };
    let title = Line::from(vec![
        Span::styled(
            " Docker Shared Services ",
            Style::new().fg(t.border_focus).add_modifier(Modifier::BOLD),
        ),
        Span::styled(format!("· {domain} "), Style::new().fg(t.text_muted)),
    ]);
    let err_span = if unhealthy > 0 {
        format!(" · {unhealthy} err")
    } else {
        String::new()
    };
    let line = Line::from(vec![
        Span::styled(
            format!(" {running}/{total} up"),
            Style::new().fg(t.green).add_modifier(Modifier::BOLD),
        ),
        Span::styled(format!(" · {healthy} ok"), Style::new().fg(t.text_muted)),
        Span::styled(
            err_span,
            Style::new().fg(t.red).add_modifier(Modifier::BOLD),
        ),
        Span::styled(" │ CPU ", Style::new().fg(t.text_muted)),
        Span::styled(
            format!("{cpu_pct:4.1}% "),
            Style::new().fg(threshold_color(cpu_norm, t)),
        ),
        Span::styled(
            sparkline(&app.cpu_history, 10),
            Style::new().fg(t.border_focus),
        ),
        Span::styled(" │ RAM ", Style::new().fg(t.text_muted)),
        Span::styled(
            format!("{ram_label} "),
            Style::new().fg(threshold_color(ram_pct, t)),
        ),
        Span::styled(
            gauge_bar(ram_pct, 8),
            Style::new().fg(threshold_color(ram_pct, t)),
        ),
        Span::styled(format!(" │ Disk {disk}"), Style::new().fg(t.text_muted)),
    ]);
    Paragraph::new(line).block(rounded_block(title, true, t))
}

/// Render an active modal (`Help`, `Confirm`, or `Presets`).
pub fn render_modal(frame: &mut Frame, modal: &Modal, help: &str, theme: &Theme) {
    let (title, body, hint) = match modal {
        Modal::Help => ("Help".to_string(), help.to_string(), "Esc closes"),
        Modal::Confirm { title, body, .. } => {
            (title.clone(), body.clone(), "y confirms · n or Esc cancels")
        }
        Modal::Presets { selected } => {
            let body = PRESETS
                .iter()
                .enumerate()
                .map(|(i, p)| {
                    let mark = if i == *selected { "▸" } else { " " };
                    let count = available_services(p).len();
                    format!("{mark} {:<14} ({count} svcs)  {}", p.name, p.summary)
                })
                .collect::<Vec<_>>()
                .join("\n");
            (
                "Stack Presets".into(),
                body,
                "↑/↓ move · Enter applies · Esc closes",
            )
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
    let block = rounded_block(format!(" {title} "), true, theme).title_bottom(format!(" {hint} "));
    frame.render_widget(
        Paragraph::new(body).wrap(Wrap { trim: false }).block(block),
        area,
    );
}
