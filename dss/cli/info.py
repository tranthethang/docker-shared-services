"""``make info``: access lines from ``service_catalog.json`` plus network and auth notes."""

from __future__ import annotations

from dss.core.service_catalog import load_catalog

HEADER = [
    "",
    "╔════════════════════════════════════════════════════════════════╗",
    "║                     Service Information                        ║",
    "╚════════════════════════════════════════════════════════════════╝",
    "",
    "Networks (three-tier topology, 10/8 plan):",
    "  • traefik_proxy — 10.0.0.0/16 (Traefik ingress + routed web services)",
    "  • backend_net   — 10.1.0.0/16 (application logic containers & workers)",
    "  • data_net      — 10.2.0.0/16 (isolated databases, caches, and storage)",
    "",
    "Services:",
]
FOOTER = [
    "",
    "Opt-in UI auth (oauth2-proxy + Zitadel; OFF by default):",
    "  • Candidates: mermaid-live-editor, temporal UI, chromadb, qdrant, kafka-ui",
    "  • Enable: set AUTH_ENABLED=true and AUTH_MIDDLEWARE=auth-default in that service .env,"
    " then restart",
    "  • Status: uv run python -m dss.cli.env summary  (shows AUTH gateway on/off)",
    "  • Setup: see oauth2-proxy/README.md and docs/configuration.md",
    "",
]


def service_lines(catalog: dict[str, dict]) -> list[str]:
    """Every catalog ``info`` line, sorted case-insensitively by its text."""
    lines = [line for entry in catalog.values() for line in entry.get("info", [])]
    return sorted(lines, key=str.casefold)


def render_info(catalog: dict[str, dict] | None = None) -> str:
    catalog = load_catalog() if catalog is None else catalog
    bullets = [f"  • {line}" for line in service_lines(catalog)]
    return "\n".join([*HEADER, *bullets, *FOOTER]) + "\n"


def main() -> None:
    print(render_info(), end="")


if __name__ == "__main__":
    main()
