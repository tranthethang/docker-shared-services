"""Catalog contract: the JSON, SERVICES, and compose directories stay aligned."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.core.config import SERVICES
from dss.core.service_catalog import catalog_problems, load_catalog
from dss.package.templates import render_readme


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


def test_default_domain_fills_placeholder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    catalog = load_catalog()
    assert catalog["adminer"]["web_ui"] == ["https://adminer.dss.localhost"]
    assert all("{domain}" not in line for entry in catalog.values() for line in entry["info"])


def test_root_env_domain_fills_placeholder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DOMAIN=env.test\n", encoding="utf-8")
    assert load_catalog()["adminer"]["web_ui"] == ["https://adminer.env.test"]

    (tmp_path / ".env").write_text("DOMAIN=\n", encoding="utf-8")
    assert load_catalog()["adminer"]["web_ui"] == ["https://adminer.dss.localhost"]


def test_domain_argument_overrides_root_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DOMAIN=env.test\n", encoding="utf-8")
    catalog = load_catalog(domain="example.test")
    assert catalog["adminer"]["web_ui"] == ["https://adminer.example.test"]
    assert catalog_problems(catalog, {}) == []


def test_package_readme_ignores_the_exporter_domain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The export ships DOMAIN=dss.localhost, so its README must show that domain.
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DOMAIN=env.test\n", encoding="utf-8")
    readme = render_readme("stack", ["adminer"])
    assert "https://adminer.dss.localhost" in readme
    assert "env.test" not in readme
