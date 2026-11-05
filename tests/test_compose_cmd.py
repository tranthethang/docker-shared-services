"""get_compose_cmd env files (root, then service) and the Traefik publish file."""

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


def _env_args(cmd: list[str]) -> list[str]:
    return [cmd[i + 1] for i, arg in enumerate(cmd) if arg == "--env-file"]


def _write(path: Path, text: str = "A=1\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_env_files_root_before_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env")
    _write(tmp_path / "adminer" / ".env")

    cmd = get_compose_cmd("adminer")
    assert _env_args(cmd) == [".env", "adminer/.env"]
    assert cmd.index("--env-file") < cmd.index("-f")


def test_env_files_root_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env")

    assert _env_args(get_compose_cmd("adminer")) == [".env"]


def test_env_files_service_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "adminer" / ".env")

    assert _env_args(get_compose_cmd("adminer")) == ["adminer/.env"]


def test_env_files_neither(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert "--env-file" not in get_compose_cmd("adminer")


def test_named_stack_adds_project_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env", "SANDBOX_NAME=projb\n")

    cmd = get_compose_cmd("postgres")
    assert cmd[cmd.index("-p") + 1] == "projb-postgres"


def test_unnamed_stack_has_no_project_flag(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / ".env", "SANDBOX_NAME=\n")

    assert "-p" not in get_compose_cmd("postgres")
