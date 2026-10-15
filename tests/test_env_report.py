"""Pin .env checks, creation, validation, prerequisites, and the summary in a temp tree."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.core.config import LEGACY_PLACEHOLDER_PASSWORD, SERVICES
from dss.core.env_files import check_env, create_env, get_services, merge_missing_env_keys
from dss.core.env_report import check_prerequisites, show_summary, validate_env

STRONG = "Strong-Password-123"


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_get_services_variants() -> None:
    assert get_services(None) == [".", *SERVICES]
    assert get_services("all") == [".", *SERVICES]
    assert get_services("redis") == ["redis"]
    assert get_services(".") == ["."]
    assert get_services("not-a-service") == []


def test_check_env_reports_missing(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tree / "redis" / ".env.example", "REDIS_PASSWORD=\n")
    assert check_env("redis") is True
    assert "redis/.env missing" in capsys.readouterr().out

    _write(tree / "redis" / ".env", "REDIS_PASSWORD=x\n")
    assert check_env("redis") is False
    assert "redis/.env exists" in capsys.readouterr().out

    assert check_env("mongodb") is False
    assert "mongodb/.env.example not found" in capsys.readouterr().out


def test_create_env_copies_example_once(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tree / "redis" / ".env.example", "REDIS_PASSWORD=\n")
    create_env("redis")
    assert (tree / "redis" / ".env").read_text(encoding="utf-8") == "REDIS_PASSWORD=\n"
    assert "Created redis/.env" in capsys.readouterr().out

    create_env("redis")
    assert "No missing .env files to create" in capsys.readouterr().out


def test_merge_missing_handles_no_trailing_newline(tree: Path) -> None:
    _write(tree / "redis" / ".env", "A=1")
    _write(tree / "redis" / ".env.example", "A=2\nB=3\nB=4\n")
    merge_missing_env_keys("redis")
    assert (tree / "redis" / ".env").read_text(encoding="utf-8") == "A=1\n\nB=3\n"


def test_merge_missing_reports_nothing_to_merge(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "redis" / ".env", "A=1\n")
    _write(tree / "redis" / ".env.example", "A=2\n")
    merge_missing_env_keys("redis")
    assert "No missing keys to merge" in capsys.readouterr().out


def test_validate_env_flags_missing_empty_and_placeholder(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "garage" / ".env", "GARAGE_RPC_SECRET=\n")
    _write(tree / "minio" / ".env", f"MINIO_ROOT_PASSWORD={LEGACY_PLACEHOLDER_PASSWORD}\n")
    assert validate_env("garage") is False
    assert validate_env("minio") is False
    out = capsys.readouterr().out
    assert "GARAGE_RPC_SECRET is empty" in out
    assert "Missing GARAGE_ADMIN_TOKEN" in out
    assert "placeholder/insecure value" in out


def test_validate_env_passes_configured_service(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "mongodb" / ".env", f"MONGO_ROOT_PASSWORD={STRONG}\n")
    assert validate_env("mongodb") is True
    assert "MONGO_ROOT_PASSWORD configured" in capsys.readouterr().out


def test_check_prerequisites_needs_root_env(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_prerequisites("redis") is False
    assert "Root environment file (.env) not found" in capsys.readouterr().out


def test_check_prerequisites_reports_service_problems(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / ".env", "DSS_SHARED_PASSWORD=x\n")
    assert check_prerequisites("redis") is False
    assert "redis: Environment file not found" in capsys.readouterr().out

    _write(tree / "mongodb" / ".env", "MONGO_ROOT_PASSWORD=\n")
    assert check_prerequisites("mongodb") is False
    assert "Mandatory variable MONGO_ROOT_PASSWORD" in capsys.readouterr().out

    _write(tree / "zitadel" / ".env", "ZITADEL_MASTERKEY=k\nZITADEL_ADMIN_PASSWORD=weak\n")
    assert check_prerequisites("zitadel") is False
    assert "ZITADEL_ADMIN_PASSWORD in zitadel/.env is too weak" in capsys.readouterr().out

    _write(tree / "zitadel" / ".env", f"ZITADEL_MASTERKEY=k\nZITADEL_ADMIN_PASSWORD={STRONG}\n")
    assert check_prerequisites("zitadel") is True


def test_show_summary_variants(tree: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tree / "traefik" / ".env", "X=1\n")
    _write(tree / "redis" / ".env", "X=1\n")
    _write(tree / "mongodb" / ".env", "MONGO_PORT=27017\n")
    _write(tree / "gitea" / ".env", "OTHER=1\n")
    _write(tree / "chromadb" / ".env", "AUTH_ENABLED=true\nAUTH_MIDDLEWARE=auth-default\n")
    _write(tree / "qdrant" / ".env", "X=1\n")

    show_summary("all")

    out = capsys.readouterr().out
    assert "Service: traefik\n  Ports: 80, 443" in out
    assert "  MONGO_PORT=27017" in out
    assert "Service: gitea\n  (no specific ports configured in .env)" in out
    assert "AUTH gateway: on (AUTH_ENABLED=true, AUTH_MIDDLEWARE=auth-default)" in out
    assert "AUTH gateway: off (AUTH_ENABLED=false, AUTH_MIDDLEWARE=auth-none)" in out
