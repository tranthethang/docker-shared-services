"""dss.core.stack: SANDBOX_NAME and SANDBOX_SUBNET_BASE from the root .env."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.core import stack
from dss.tui.docker_state import list_service_statuses


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _env(root: Path, text: str) -> None:
    (root / ".env").write_text(text, encoding="utf-8")


def test_defaults_without_env_file(root: Path) -> None:
    assert stack.stack_name() == ""
    assert stack.project_name("postgres") == "postgres"
    assert stack.network_pairs() == [
        "traefik_proxy:10.0.0.0/16",
        "backend_net:10.1.0.0/16",
        "data_net:10.2.0.0/16",
    ]


def test_empty_values_keep_defaults(root: Path) -> None:
    _env(root, "SANDBOX_NAME=\nSANDBOX_SUBNET_BASE=0\n")
    assert stack.stack_name() == ""
    assert stack.network_name("data_net") == "data_net"


def test_named_stack(root: Path) -> None:
    _env(root, "SANDBOX_NAME=projb\nSANDBOX_SUBNET_BASE=10\n")
    assert stack.project_name("postgres") == "projb-postgres"
    assert stack.network_pairs() == [
        "projb_traefik_proxy:10.10.0.0/16",
        "projb_backend_net:10.11.0.0/16",
        "projb_data_net:10.12.0.0/16",
    ]


@pytest.mark.parametrize("value", ["ProjB", "-x", "a b", "a.b"])
def test_invalid_name(root: Path, value: str) -> None:
    _env(root, f"SANDBOX_NAME={value}\n")
    with pytest.raises(ValueError, match="SANDBOX_NAME"):
        stack.stack_name()


@pytest.mark.parametrize("value", ["abc", "-1", "254", "256"])
def test_invalid_subnet_base(root: Path, value: str) -> None:
    _env(root, f"SANDBOX_SUBNET_BASE={value}\n")
    with pytest.raises(ValueError, match="SANDBOX_SUBNET_BASE"):
        stack.subnet_base()


def test_main_prints_pairs_and_name(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _env(root, "SANDBOX_NAME=projb\nSANDBOX_SUBNET_BASE=4\n")
    assert stack.main(["stack"]) == 0
    assert capsys.readouterr().out.splitlines()[0] == "projb_traefik_proxy:10.4.0.0/16"
    assert stack.main(["stack", "name"]) == 0
    assert capsys.readouterr().out.strip() == "projb"


def test_main_reports_errors(root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _env(root, "SANDBOX_NAME=BAD\n")
    assert stack.main(["stack"]) == 1
    assert "SANDBOX_NAME" in capsys.readouterr().err
    assert stack.main(["stack", "x"]) == stack.EXIT_USAGE


class _Container:
    def __init__(self, project: str) -> None:
        self.labels = {
            "com.docker.compose.project": project,
            "com.docker.compose.service": "db",
        }
        self.name = f"{project}-db"
        self.status = "running"
        self.attrs: dict[str, object] = {}

    def reload(self) -> None:
        return None


class _Client:
    def __init__(self, projects: list[str]) -> None:
        self.containers = self
        self._projects = projects

    def list(self, all: bool = True) -> list[_Container]:  # noqa: A002
        return [_Container(p) for p in self._projects]


def _running(rows: list, name: str) -> int:
    return next(r for r in rows if r.name == name).container_count


def test_tui_maps_prefixed_project_to_service(root: Path) -> None:
    _env(root, "SANDBOX_NAME=projb\n")
    rows = list_service_statuses(_Client(["projb-postgres", "postgres"]))
    assert _running(rows, "postgres") == 1


def test_tui_unnamed_stack_ignores_prefixed_projects(root: Path) -> None:
    rows = list_service_statuses(_Client(["projb-postgres"]))
    assert _running(rows, "postgres") == 0
