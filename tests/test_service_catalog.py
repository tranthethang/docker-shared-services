"""Catalog contract: the JSON, SERVICES, and compose directories stay aligned."""

from __future__ import annotations

from pathlib import Path

from config import SERVICES
from service_catalog import catalog_problems, load_catalog


def test_catalog_problems_are_empty() -> None:
    # An empty compose map skips container-name drift. `make validate` checks
    # those names with `docker compose config`, which unit tests do not run.
    assert catalog_problems(load_catalog(), {}) == []


def test_every_compose_directory_is_in_the_catalog(repo_root: Path) -> None:
    catalog = load_catalog()
    compose_dirs = sorted(path.parent.name for path in repo_root.glob("*/docker-compose.yml"))
    assert compose_dirs
    for name in compose_dirs:
        assert name in catalog
        assert name in SERVICES
    assert set(catalog) == set(SERVICES)
