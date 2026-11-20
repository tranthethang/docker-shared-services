//! `dss info`: access lines from the catalog plus network notes.

use crate::catalog::Catalog;
use crate::stack::{network_pairs, NETWORK_BASES};

const HEADER: &[&str] = &[
    "",
    "╔════════════════════════════════════════════════════════════════╗",
    "║                     Service Information                        ║",
    "╚════════════════════════════════════════════════════════════════╝",
    "",
    "Networks (three-tier topology, 10/8 plan):",
];
const NETWORK_ROLES: [&str; 3] = [
    "Traefik ingress + routed web services",
    "application logic containers & workers",
    "isolated databases, caches, and storage",
];
const FOOTER: &[&str] = &[
    "",
    "Opt-in UI auth (oauth2-proxy + OIDC issuer; OFF by default):",
    "  • Candidates: mermaid-live-editor, temporal UI, chromadb, qdrant, kafka-ui",
    "  • Enable: set AUTH_ENABLED=true and AUTH_MIDDLEWARE=auth-default in that service .env, then restart",
    "  • Status: dss env summary  (shows AUTH gateway on/off)",
    "  • Setup: see oauth2-proxy/README.md and docs/configuration.md",
    "",
];

/// Every catalog `info` line, sorted case-insensitively.
pub fn service_lines(catalog: &Catalog) -> Vec<String> {
    let mut lines: Vec<String> = catalog.values().flat_map(|e| e.info.clone()).collect();
    lines.sort_by_key(|l| l.to_lowercase());
    lines
}

fn network_lines(pairs: &[String]) -> Vec<String> {
    let parsed: Vec<(&str, &str)> = pairs.iter().filter_map(|p| p.split_once(':')).collect();
    let width = parsed
        .iter()
        .map(|(n, _)| n.chars().count())
        .max()
        .unwrap_or(0);
    parsed
        .iter()
        .zip(NETWORK_ROLES)
        .map(|((name, subnet), role)| format!("  • {name:<width$} — {subnet} ({role})"))
        .collect()
}

/// Render the full `dss info` text.
pub fn render_info(catalog: &Catalog, pairs: &[String]) -> String {
    let mut out: Vec<String> = HEADER.iter().map(|s| s.to_string()).collect();
    out.extend(network_lines(pairs));
    out.extend(["".into(), "Services:".into()]);
    out.extend(
        service_lines(catalog)
            .into_iter()
            .map(|l| format!("  • {l}")),
    );
    out.extend(FOOTER.iter().map(|s| s.to_string()));
    out.join("\n") + "\n"
}

/// `dss info` with the current stack and catalog.
pub fn info_text(catalog: &Catalog) -> Result<String, String> {
    debug_assert_eq!(NETWORK_BASES.len(), NETWORK_ROLES.len());
    Ok(render_info(catalog, &network_pairs()?))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::catalog::{parse_catalog, DEFAULT_DOMAIN};

    fn catalog(domain: &str) -> Catalog {
        parse_catalog(include_str!("../service_catalog.json"), domain).unwrap()
    }

    #[test]
    fn prints_urls_with_the_domain_substituted() {
        let text = render_info(&catalog("example.test"), &[]);
        assert!(text.contains("  • Adminer - https://adminer.example.test"));
        assert!(!text.contains("{domain}"));
    }

    #[test]
    fn lines_are_sorted_case_insensitively() {
        let lines = service_lines(&catalog(DEFAULT_DOMAIN));
        let mut sorted = lines.clone();
        sorted.sort_by_key(|l| l.to_lowercase());
        assert_eq!(lines, sorted);
    }

    #[test]
    fn lists_networks_with_roles() {
        let pairs = vec![
            "traefik_proxy:10.0.0.0/16".to_string(),
            "data_net:10.2.0.0/16".to_string(),
        ];
        let text = render_info(&catalog(DEFAULT_DOMAIN), &pairs);
        assert!(text
            .contains("  • traefik_proxy — 10.0.0.0/16 (Traefik ingress + routed web services)"));
        assert!(text
            .contains("  • data_net      — 10.2.0.0/16 (application logic containers & workers)"));
    }
}
