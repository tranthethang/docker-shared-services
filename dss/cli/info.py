"""``make info``: access lines from ``service_catalog.json`` plus network and auth notes."""

from __future__ import annotations

from typing import Any

from dss.core.service_catalog import load_catalog
from dss.core.stack import NETWORK_BASES, network_pairs

HEADER = [
    "",
    "╔════════════════════════════════════════════════════════════════╗",
    "║                     Service Information                        ║",
    "╚════════════════════════════════════════════════════════════════╝",
    "",
    "Networks (three-tier topology, 10/8 plan):",
]
NETWORKS_END = [
    "",
    "Services:",
]
NETWORK_ROLES = {
    "traefik_proxy": "Traefik ingress + routed web services",
    "backend_net": "application logic containers & workers",
    "data_net": "isolated databases, caches, and storage",
}
FOOTER = [
    "",
    "Opt-in UI auth (oauth2-proxy + OIDC issuer; OFF by default):",
    "  • Candidates: mermaid-live-editor, temporal UI, chromadb, qdrant, kafka-ui",
    "  • Enable: set AUTH_ENABLED=true and AUTH_MIDDLEWARE=auth-default in that service .env,"
    " then restart",
    "  • Status: uv run python -m dss.cli.env summary  (shows AUTH gateway on/off)",
    "  • Setup: see oauth2-proxy/README.md and docs/configuration.md",
    "",
]


def service_lines(catalog: dict[str, dict[str, Any]]) -> list[str]:
    """Every catalog ``info`` line, sorted case-insensitively by its text."""
    lines = [line for entry in catalog.values() for line in entry.get("info", [])]
    return sorted(lines, key=str.casefold)


def network_lines() -> list[str]:
    """One line per shared network, with the ``SANDBOX_NAME`` prefix and subnet in effect."""
    pairs = [pair.split(":", 1) for pair in network_pairs()]
    width = max(len(name) for name, _ in pairs)
    return [
        f"  • {name.ljust(width)} — {subnet} ({NETWORK_ROLES[base]})"
        for base, (name, subnet) in zip(NETWORK_BASES, pairs, strict=True)
    ]


def render_info(catalog: dict[str, dict[str, Any]] | None = None) -> str:
    catalog = load_catalog() if catalog is None else catalog
    bullets = [f"  • {line}" for line in service_lines(catalog)]
    return "\n".join([*HEADER, *network_lines(), *NETWORKS_END, *bullets, *FOOTER]) + "\n"


def main() -> None:
    print(render_info(), end="")


if __name__ == "__main__":
    main()
