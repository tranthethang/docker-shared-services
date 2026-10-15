"""Selection logic behind the package wizard. Imports no Textual or Rich, so tests can run it."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from dss.core.config import PACKAGE_DEFAULT_SERVICES, PACKAGE_REQUIRES, SERVICES
from dss.core.dependencies import direct_dependencies
from dss.core.service_catalog import CATEGORIES, load_catalog
from dss.package.export import (
    partition_selection,
    repo_root,
    service_requires_traefik,
    validate_stack_name,
)

SelectionState = Literal["checked", "added", "none"]

DEFAULTS = frozenset(PACKAGE_DEFAULT_SERVICES)
CATALOG = load_catalog()
TRAEFIK_USERS = [name for name in SERVICES if name != "traefik" and service_requires_traefik(name)]

MARKS: dict[SelectionState, str] = {"checked": "[x]", "added": "[+]", "none": "[ ]"}
STATE_LABELS: dict[SelectionState, str] = {
    "checked": "checked",
    "added": "added as a dependency",
    "none": "not selected",
}


def requires(service: str) -> list[str]:
    needs = direct_dependencies(service)
    if service != "traefik" and service in TRAEFIK_USERS:
        needs = ["traefik", *needs]
    return [name for name in SERVICES if name in needs]


def required_by(service: str) -> list[str]:
    users = set(PACKAGE_REQUIRES.get(service, []))
    if service == "traefik":
        users.update(TRAEFIK_USERS)
    return [name for name in SERVICES if name in users]


def matches(service: str, query: str) -> bool:
    if not query:
        return True
    entry = CATALOG[service]
    haystack = f"{service} {entry['category']} {entry['description']}".lower()
    return query.lower() in haystack


def grouped_matches(query: str) -> list[tuple[str, list[str]]]:
    """(category, services) pairs in ``CATEGORIES`` order, without empty categories."""
    groups: list[tuple[str, list[str]]] = []
    for category in CATEGORIES:
        members = [
            name
            for name in SERVICES
            if CATALOG[name]["category"] == category and matches(name, query)
        ]
        if members:
            groups.append((category, members))
    return groups


def added_dependencies(checked: set[str]) -> set[str]:
    """Services the exporter adds on top of ``checked``."""
    if not checked:
        return set()
    _checked, added = partition_selection(sorted(checked))
    return set(added)


def toggle(checked: set[str], service: str) -> set[str]:
    """Return a new set. Toggling an auto-added dependency makes it an explicit choice."""
    if service in checked:
        return checked - {service}
    return checked | {service}


def selection_state(service: str, checked: set[str], added: set[str]) -> SelectionState:
    if service in checked:
        return "checked"
    if service in added:
        return "added"
    return "none"


def ordered_selection(checked: set[str]) -> list[str]:
    return [service for service in SERVICES if service in checked]


def stack_name_error(name: str, root: Path | None = None) -> str | None:
    """Why ``name`` cannot be used, or None when ``dist/<name>/`` can be written."""
    try:
        validate_stack_name(name)
    except ValueError as exc:
        return str(exc)
    if ((root or repo_root()) / "dist" / name).exists():
        return f"dist/{name}/ already exists"
    return None


def confirm_rows(checked: list[str], added: list[str]) -> list[tuple[str, str, str, str]]:
    """(service, category, first web UI, reason) for every packaged service."""
    checked_set = set(checked)
    rows: list[tuple[str, str, str, str]] = []
    for service in SERVICES:
        if service not in checked_set and service not in added:
            continue
        entry = CATALOG[service]
        web_ui = entry["web_ui"][0] if entry["web_ui"] else "—"
        reason = "checked" if service in checked_set else "dependency"
        rows.append((service, entry["category"], web_ui, reason))
    return rows
