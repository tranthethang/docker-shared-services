"""get_compose_cmd adds the Traefik publish file only when TRAEFIK_HTTP_PORT is set."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.cli.compose import TRAEFIK_PUBLISH_FILE, get_compose_cmd


def _write_traefik_env(root: Path, text: str) -> None:
    env_path = root / "traefik" / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(text, encoding="utf-8")


def test_traefik_without_port_has_no_publish_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert TRAEFIK_PUBLISH_FILE not in get_compose_cmd("traefik")

    _write_traefik_env(tmp_path, "TRAEFIK_BIND=127.0.0.1\nTRAEFIK_HTTP_PORT=\n")
    assert TRAEFIK_PUBLISH_FILE not in get_compose_cmd("traefik")


def test_traefik_with_port_adds_publish_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_traefik_env(tmp_path, "TRAEFIK_HTTP_PORT=8081\n")

    cmd = get_compose_cmd("traefik")
    assert cmd[-2:] == ["-f", TRAEFIK_PUBLISH_FILE]


def test_other_services_ignore_traefik_port(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write_traefik_env(tmp_path, "TRAEFIK_HTTP_PORT=8081\n")

    assert get_compose_cmd("postgres") == [
        "docker",
        "compose",
        "--project-directory",
        "postgres",
        "-f",
        "docker-compose.shared.yml",
        "-f",
        "postgres/docker-compose.yml",
    ]
