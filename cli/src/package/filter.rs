//! Limit the root `.env.example` and the catalog to a service selection.

use crate::catalog::Catalog;

/// Banner title (text before " - ") -> service directory. The longest match wins.
const BANNERS: &[(&str, &str)] = &[
    ("TRAEFIK", "traefik"),
    ("POSTGRES", "postgres"),
    ("PGVECTOR", "pgvector"),
    ("MySQL 8", "mysql8"),
    ("MARIADB", "mariadb"),
    ("MONGODB", "mongodb"),
    ("REDIS INSIGHT", "redisinsight"),
    ("REDIS", "redis"),
    ("RABBITMQ", "rabbitmq"),
    ("MEMCACHED", "memcached"),
    ("MAILPIT", "mailpit"),
    ("MINIO", "minio"),
    ("ADMINER", "adminer"),
    ("DOCKGE", "dockge"),
    ("PORTAINER", "portainer"),
    ("GITEA", "gitea"),
    ("SONARQUBE", "sonarqube"),
    ("JENKINS", "jenkins"),
    ("CONCOURSE", "concourse"),
    ("ACT RUNNER", "act_runner"),
    ("OTEL", "otel"),
    ("n8n", "n8n"),
    ("Node-RED", "node-red"),
    ("DOZZLE", "dozzle"),
    ("CHROMADB", "chromadb"),
    ("QDRANT", "qdrant"),
    ("APPSMITH", "appsmith"),
    ("TEMPORAL", "temporal"),
    ("POCKETBASE", "pocketbase"),
    ("SUPABASE", "supabase"),
    ("CENTRIFUGO", "centrifugo"),
    ("GOTENBERG", "gotenberg"),
    ("LIBREOFFICE WRITER", "libreoffice-writer"),
    ("MERMAID", "mermaid-live-editor"),
    ("HASURA", "hasura"),
];

fn banner_service(title: &str) -> Option<&'static str> {
    BANNERS
        .iter()
        .filter(|(key, _)| title == *key || title.starts_with(&format!("{key} ")))
        .max_by_key(|(key, _)| key.len())
        .map(|(_, service)| *service)
}

fn is_sep(line: &str) -> bool {
    let t = line.trim_end();
    t.strip_prefix("# ")
        .is_some_and(|rest| rest.len() >= 10 && rest.chars().all(|c| c == '='))
}

/// Index of the closing separator when `start` opens a banner header.
fn header_close(lines: &[&str], start: usize) -> Option<usize> {
    if start >= lines.len() || !is_sep(lines[start]) {
        return None;
    }
    let mut saw_comment = false;
    let mut i = start + 1;
    while i < lines.len() && !is_sep(lines[i]) {
        let t = lines[i].trim();
        if t.starts_with('#') {
            saw_comment = true;
        } else if !t.is_empty() {
            return None;
        }
        i += 1;
    }
    (saw_comment && i < lines.len()).then_some(i)
}

fn banner_title(lines: &[&str], start: usize, close: usize) -> String {
    lines[start + 1..close]
        .iter()
        .map(|l| l.trim())
        .find(|l| l.starts_with('#'))
        .map(|l| {
            l[1..]
                .trim()
                .split(" - ")
                .next()
                .unwrap_or("")
                .trim()
                .to_string()
        })
        .unwrap_or_default()
}

/// `(start, next_start, title)` for each banner and its body.
fn spans(lines: &[&str]) -> Vec<(usize, usize, String)> {
    let mut headers = Vec::new();
    let mut i = 0;
    while i < lines.len() {
        match header_close(lines, i) {
            Some(close) => {
                headers.push((i, banner_title(lines, i, close)));
                i = close + 1;
            }
            None => i += 1,
        }
    }
    let ends: Vec<usize> = headers
        .iter()
        .skip(1)
        .map(|(s, _)| *s)
        .chain([lines.len()])
        .collect();
    headers
        .into_iter()
        .zip(ends)
        .map(|((start, title), end)| (start, end, title))
        .collect()
}

#[cfg(test)]
/// Banner titles that no service owns. They are dropped from a package.
pub fn unmapped_env_banners(text: &str) -> Vec<String> {
    let lines: Vec<&str> = text.split_inclusive('\n').collect();
    spans(&lines)
        .into_iter()
        .map(|(_, _, title)| title)
        .filter(|t| {
            !t.starts_with("SHARED PASSWORD")
                && t != "Security Notes"
                && banner_service(t).is_none()
        })
        .collect()
}

/// Keep the preamble, the shared-password block, selected service blocks, and Security Notes.
pub fn filter_env_example(text: &str, services: &[String]) -> String {
    let lines: Vec<&str> = text.split_inclusive('\n').collect();
    let spans = spans(&lines);
    if spans.is_empty() {
        return text.to_string();
    }
    let shared_end = spans
        .iter()
        .find(|(_, _, t)| t.starts_with("SHARED PASSWORD"))
        .map_or(0, |(_, end, _)| *end);
    let mut out = lines[..shared_end].concat();
    for (start, end, title) in &spans {
        if title.starts_with("SHARED PASSWORD") {
            continue;
        }
        if title == "Security Notes" {
            out.push_str(&lines[*start..].concat());
            break;
        }
        if banner_service(title).is_some_and(|s| services.iter().any(|x| x == s)) {
            out.push_str(&lines[*start..*end].concat());
        }
    }
    if !out.is_empty() && !out.ends_with('\n') {
        out.push('\n');
    }
    out
}

/// The catalog limited to `services`, as pretty JSON with `{domain}` left in place.
pub fn filter_catalog(raw: &Catalog, services: &[String]) -> Result<String, String> {
    let kept: Catalog = raw
        .iter()
        .filter(|(k, _)| services.contains(k))
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect();
    serde_json::to_string_pretty(&kept)
        .map(|s| s + "\n")
        .map_err(|e| e.to_string())
}

/// `dss-package.json`: the services the exported tree manages.
pub fn manifest(services: &[String]) -> Result<String, String> {
    serde_json::to_string_pretty(&serde_json::json!({ "services": services }))
        .map(|s| s + "\n")
        .map_err(|e| e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;

    const SEP: &str = "# ==========================================\n";

    fn banner(title: &str) -> String {
        format!("{SEP}# {title} - settings\n{SEP}")
    }

    fn sample() -> String {
        format!(
            "HEAD=1\n{}DSS_SHARED_PASSWORD=x\n{}REDIS_PORT=6379\n{}POSTGRES16_PORT=5432\n{}MAILPIT_PORT=1025\n{}# keep\n",
            banner("SHARED PASSWORD"),
            banner("REDIS"),
            banner("POSTGRES"),
            banner("MAILPIT"),
            banner("Security Notes"),
        )
    }

    fn names(items: &[&str]) -> Vec<String> {
        items.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn keeps_selected_services_and_drops_unrelated_ones() {
        let out = filter_env_example(&sample(), &names(&["redis"]));
        assert!(out.contains("HEAD=1") && out.contains("DSS_SHARED_PASSWORD=x"));
        assert!(out.contains("REDIS_PORT=6379"));
        assert!(!out.contains("POSTGRES16_PORT") && !out.contains("MAILPIT_PORT"));
        assert!(out.contains("# keep"), "Security Notes stay");
    }

    #[test]
    fn longest_banner_key_wins() {
        let text = format!("{}{}", banner("REDIS INSIGHT"), "X=1\n");
        assert!(!filter_env_example(&text, &names(&["redis"])).contains("X=1"));
        assert!(filter_env_example(&text, &names(&["redisinsight"])).contains("X=1"));
    }

    #[test]
    fn reports_unmapped_banners() {
        let text = format!("{}{}", banner("MYSTERY"), banner("REDIS"));
        assert_eq!(unmapped_env_banners(&text), ["MYSTERY"]);
    }

    #[test]
    fn real_env_example_has_no_unmapped_banners() {
        let text = std::fs::read_to_string("../.env.example").unwrap();
        assert_eq!(unmapped_env_banners(&text), Vec::<String>::new());
    }

    #[test]
    fn text_without_banners_is_unchanged() {
        assert_eq!(filter_env_example("A=1\n", &names(&["redis"])), "A=1\n");
    }

    #[test]
    fn catalog_and_manifest_hold_only_selected_services() {
        let all =
            crate::catalog::parse_catalog(include_str!("../../service_catalog.json"), "{domain}")
                .unwrap();
        let json = filter_catalog(&all, &names(&["redis", "traefik"])).unwrap();
        assert!(json.contains("\"redis\"") && json.contains("\"traefik\""));
        assert!(!json.contains("\"postgres\""));
        assert!(json.contains("{domain}"));
        assert_eq!(
            crate::config::select_services(&manifest(&names(&["redis"])).unwrap()).unwrap(),
            ["redis"]
        );
    }
}
