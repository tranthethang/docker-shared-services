//! Curated Stack Presets for quick multi-service selection (`p` modal).

use super::app::{App, Modal};
use crate::config::active_services;
use crossterm::event::KeyCode;

/// A named stack preset with a short description and candidate service names.
#[derive(Clone, Copy, Debug)]
pub struct Preset {
    pub name: &'static str,
    pub summary: &'static str,
    pub services: &'static [&'static str],
}

pub const PRESETS: &[Preset] = &[
    Preset {
        name: "Core Infra",
        summary: "Gateway, Postgres, Redis, and live log viewer",
        services: &["traefik", "postgres", "redis", "dozzle"],
    },
    Preset {
        name: "AI Dev",
        summary: "Vector stores, LLM proxy, and web crawler",
        services: &[
            "traefik",
            "pgvector",
            "qdrant",
            "chromadb",
            "litellm",
            "crawl4ai",
            "hindsight",
        ],
    },
    Preset {
        name: "Observability",
        summary: "OpenTelemetry, Dozzle logs, Bugsink, and Mailpit",
        services: &["traefik", "otel", "dozzle", "bugsink", "mailpit"],
    },
    Preset {
        name: "CI/CD",
        summary: "Gitea, runner, Woodpecker CI, and Verdaccio",
        services: &["traefik", "gitea", "act_runner", "woodpecker", "verdaccio"],
    },
];

/// Services in `preset` that exist in the current repository's `active_services()`.
pub fn available_services(preset: &Preset) -> Vec<&'static str> {
    let active = active_services();
    preset
        .services
        .iter()
        .copied()
        .filter(|s| active.contains(s))
        .collect()
}

/// Handle key events inside `Modal::Presets`.
pub fn handle_key(app: &mut App, selected: usize, code: KeyCode) {
    match code {
        KeyCode::Down | KeyCode::Char('j') => {
            app.modal = Some(Modal::Presets {
                selected: (selected + 1).min(PRESETS.len().saturating_sub(1)),
            });
        }
        KeyCode::Up | KeyCode::Char('k') => {
            app.modal = Some(Modal::Presets {
                selected: selected.saturating_sub(1),
            });
        }
        KeyCode::Enter => {
            if let Some(preset) = PRESETS.get(selected) {
                app.manage = available_services(preset)
                    .into_iter()
                    .filter(|s| !app.locked.contains_key(*s))
                    .map(str::to_string)
                    .collect();
                app.manage_dirty = true;
                app.status = format!(
                    "Preset {} selected ({} services)",
                    preset.name,
                    app.manage.len()
                );
            }
            app.modal = None;
        }
        KeyCode::Esc | KeyCode::Char('q') => app.modal = None,
        _ => {}
    }
}
