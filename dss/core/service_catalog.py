"""Service catalog: what each service is, for the package wizard, README, and ``make info``.

Standard library only. The data lives in ``service_catalog.json`` next to this file.
"""

from __future__ import annotations

import json
from pathlib import Path

from dss.core.config import SERVICES

CATALOG_PATH = Path(__file__).resolve().parent / "service_catalog.json"

# Display order of categories in the wizard and README.
CATEGORIES = [
    "Database",
    "Cache & Queue",
    "Storage",
    "Auth & Gateway",
    "CI/CD",
    "Workflow & Automation",
    "Observability",
    "Admin UI",
    "AI & Search",
    "Dev Tools",
]

_FIELDS = {"category", "description", "containers", "web_ui", "info"}


def load_catalog(path: Path | None = None) -> dict[str, dict]:
    with open(path or CATALOG_PATH, encoding="utf-8") as handle:
        return json.load(handle)


def _is_str_list(value) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def catalog_problems(catalog: dict, compose_services: dict[str, list[str]]) -> list[str]:
    """Return drift errors between the catalog, ``SERVICES``, and compose service names."""
    problems: list[str] = []
    if not isinstance(catalog, dict):
        return ["catalog: top level must be a JSON object"]

    for name in SERVICES:
        if name not in catalog:
            problems.append(f"{name}: missing from service_catalog.json")
    for name in catalog:
        if name not in SERVICES:
            problems.append(f"{name}: in service_catalog.json but not in SERVICES")

    for name in SERVICES:
        entry = catalog.get(name)
        if entry is None:
            continue
        if not isinstance(entry, dict):
            problems.append(f"{name}: entry must be an object")
            continue
        fields = set(entry)
        if fields != _FIELDS:
            missing = sorted(_FIELDS - fields)
            extra = sorted(fields - _FIELDS)
            detail = ", ".join(
                part
                for part in (
                    f"missing {missing}" if missing else "",
                    f"unexpected {extra}" if extra else "",
                )
                if part
            )
            problems.append(f"{name}: fields {detail}")
        category = entry.get("category")
        if category not in CATEGORIES:
            problems.append(f"{name}: category {category!r} is not one of {CATEGORIES}")
        description = entry.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{name}: description must be a non-empty string")
        containers = entry.get("containers")
        if not _is_str_list(containers):
            problems.append(f"{name}: containers must be a list of strings")
        elif name in compose_services and set(containers) != set(compose_services[name]):
            problems.append(
                f"{name}: containers {sorted(containers)} != compose services "
                f"{sorted(compose_services[name])}"
            )
        web_ui = entry.get("web_ui")
        if not _is_str_list(web_ui):
            problems.append(f"{name}: web_ui must be a list of strings")
        else:
            for url in web_ui:
                if not url.startswith("https://"):
                    problems.append(f"{name}: web_ui URL {url!r} must start with https://")
        if not _is_str_list(entry.get("info")):
            problems.append(f"{name}: info must be a list of strings")
    return problems
