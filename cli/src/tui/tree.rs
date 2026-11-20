//! Category-grouped and A-Z sorted service tree for the TUI Services table.

use super::app::App;
use super::widgets::{format_bytes, health_style, rounded_block, state_dot};
use crate::catalog::{Catalog, CATEGORIES};
use crate::docker::state::ServiceStatus;
use ratatui::layout::Constraint;
use ratatui::style::{Modifier, Style};
use ratatui::widgets::{Cell, Row, Table};
use std::collections::BTreeSet;

/// One visible row in the grouped Services table.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum TreeRow {
    Group {
        category: &'static str,
        running: usize,
        total: usize,
        collapsed: bool,
    },
    Service {
        index: usize,
    },
}

/// Group `rows` by `catalog::CATEGORIES` (plus `"Other"`), sort A-Z within each group,
/// apply `filter` and `active_only`, and respect `collapsed` (auto-expanding when `filter` is non-empty).
pub fn build_tree(
    rows: &[ServiceStatus],
    catalog: &Catalog,
    collapsed: &BTreeSet<String>,
    filter: &str,
    active_only: bool,
) -> Vec<TreeRow> {
    let needle = filter.trim().to_lowercase();
    let filtering = !needle.is_empty();
    let mut out = Vec::new();

    for &category in CATEGORIES.iter().chain(std::iter::once(&"Other")) {
        let mut group_indices: Vec<usize> = rows
            .iter()
            .enumerate()
            .filter(|(_, r)| {
                let cat = catalog
                    .get(&r.name)
                    .map(|e| e.category.as_str())
                    .unwrap_or("Other");
                if category == "Other" {
                    !CATEGORIES.contains(&cat)
                } else {
                    cat == category
                }
            })
            .map(|(i, _)| i)
            .collect();

        if group_indices.is_empty() {
            continue;
        }

        let total = group_indices.len();
        let running = group_indices
            .iter()
            .filter(|&&i| rows[i].running_count > 0)
            .count();

        group_indices.retain(|&i| {
            let r = &rows[i];
            let matches_text = !filtering || r.name.to_lowercase().contains(&needle);
            let matches_active = !active_only || r.running_count > 0;
            matches_text && matches_active
        });

        if group_indices.is_empty() {
            continue;
        }

        group_indices.sort_by(|&a, &b| {
            rows[a]
                .name
                .to_lowercase()
                .cmp(&rows[b].name.to_lowercase())
        });

        let is_collapsed = !filtering && collapsed.contains(category);
        out.push(TreeRow::Group {
            category,
            running,
            total,
            collapsed: is_collapsed,
        });

        if !is_collapsed {
            for index in group_indices {
                out.push(TreeRow::Service { index });
            }
        }
    }

    out
}

/// Collapse or expand a category group and keep selection on the group when collapsing.
pub fn fold_category(app: &mut App, category: &'static str, collapse: bool) {
    if collapse {
        app.collapsed.insert(category.to_string());
        if let Some(i) = app
            .tree_rows()
            .iter()
            .position(|t| matches!(t, TreeRow::Group { category: c, .. } if *c == category))
        {
            app.selected = i;
        }
    } else {
        app.collapsed.remove(category);
    }
    app.clamp();
}

/// Collapse or expand the group containing the currently selected row.
pub fn set_group_collapsed(app: &mut App, collapse: bool) {
    let cat = match app.selected_tree_row() {
        Some(TreeRow::Group { category, .. }) => Some(category),
        Some(TreeRow::Service { index }) => app.rows.get(index).map(|r| {
            let c = app
                .catalog
                .get(&r.name)
                .map(|e| e.category.as_str())
                .unwrap_or("Other");
            CATEGORIES
                .iter()
                .copied()
                .find(|&k| k == c)
                .unwrap_or("Other")
        }),
        None => None,
    };
    if let Some(c) = cat {
        fold_category(app, c, collapse);
    }
}

/// Render the grouped `Services` table.
pub fn services_table(app: &App) -> Table<'static> {
    let t = &app.theme;
    let vm_quarter = app
        .capacity
        .map(|c| c.mem_total_bytes / 4)
        .filter(|&q| q > 0);
    let rows: Vec<Row> = app
        .tree_rows()
        .into_iter()
        .map(|entry| match entry {
            TreeRow::Group {
                category,
                running,
                total,
                collapsed,
            } => {
                let arrow = if collapsed { "▸" } else { "▾" };
                let style = if running > 0 {
                    t.border_focus
                } else {
                    t.text_muted
                };
                let cat_style = Style::new().fg(style).add_modifier(Modifier::BOLD);
                Row::new(vec![
                    Cell::from(arrow).style(cat_style),
                    Cell::from(format!("{category} ({running}/{total})")).style(cat_style),
                    Cell::from(""),
                    Cell::from(""),
                ])
                .style(Style::new().bg(t.surface_elevated))
            }
            TreeRow::Service { index } => {
                let r = &app.rows[index];
                let locked = app.locked.contains_key(&r.name);
                let (dot, dot_style) = state_dot(r.state, t);
                let mark = if locked {
                    "—"
                } else if app.manage.contains(&r.name) {
                    "✓"
                } else {
                    " "
                };
                let name_style =
                    Style::new().fg(if locked { t.text_muted } else { t.text_primary });
                let (cpu, mem) = app.service_stats(r);
                let usage = if mem > 0 || cpu > 0.0 {
                    format!("{} {:>4.1}%", format_bytes(mem), cpu)
                } else {
                    "—".into()
                };
                let usage_style = if vm_quarter.is_some_and(|q| mem > q) {
                    Style::new().fg(t.amber).add_modifier(Modifier::BOLD)
                } else {
                    Style::new().fg(t.text_muted)
                };
                Row::new(vec![
                    Cell::from(format!("{mark}{dot}")).style(dot_style),
                    Cell::from(format!("  {}", r.name)).style(name_style),
                    Cell::from(r.health).style(health_style(r.health, t)),
                    Cell::from(usage).style(usage_style),
                ])
            }
        })
        .collect();
    let widths = [
        Constraint::Length(3),
        Constraint::Min(18),
        Constraint::Length(10),
        Constraint::Length(12),
    ];
    Table::new(rows, widths)
        .header(
            Row::new(["", "Service", "Health", "MEM / CPU"])
                .style(Style::new().fg(t.text_muted).add_modifier(Modifier::BOLD)),
        )
        .row_highlight_style(
            Style::new()
                .bg(t.surface_elevated)
                .add_modifier(Modifier::BOLD),
        )
        .block(rounded_block(" Services ", !app.filter_mode, t))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::docker::state::ServiceStatus;

    fn svc(name: &str, running: usize) -> ServiceStatus {
        ServiceStatus {
            name: name.into(),
            state: if running > 0 { "running" } else { "absent" },
            health: "none",
            container_count: running,
            running_count: running,
            containers: vec![],
        }
    }

    #[test]
    fn groups_sorts_az_and_auto_expands_on_filter() {
        let cat = crate::catalog::load_catalog();
        let rows = vec![svc("redis", 0), svc("postgres", 1), svc("mariadb", 0)];
        let collapsed = BTreeSet::from(["Database".to_string()]);
        let tree = build_tree(&rows, &cat, &collapsed, "", false);
        assert_eq!(tree.len(), 3); // Database(collapsed), Cache & Queue, redis
        let filtered = build_tree(&rows, &cat, &collapsed, "maria", false);
        assert_eq!(filtered.len(), 2); // Database auto-expanded + mariadb
        let active = build_tree(&rows, &cat, &BTreeSet::new(), "", true);
        assert_eq!(active.len(), 2); // Database + postgres
    }
}
