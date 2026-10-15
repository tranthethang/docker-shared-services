"""oauth2-proxy stays a label until the Zitadel client id and secret are set."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.core.start_gate import label_only_reason, label_only_services
from dss.tui.compose_ops import plan_manage_changes


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_other_services_are_startable() -> None:
    assert label_only_reason("redis") is None


def test_oauth2_proxy_is_label_only_without_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert "missing" in (label_only_reason("oauth2-proxy") or "")

    _write(
        tmp_path / "oauth2-proxy" / ".env",
        "OAUTH2_PROXY_CLIENT_ID=\nOAUTH2_PROXY_CLIENT_SECRET=\n",
    )
    assert label_only_services() == frozenset({"oauth2-proxy"})
    assert "OIDC client not set" in (label_only_reason("oauth2-proxy") or "")

    _write(
        tmp_path / "oauth2-proxy" / ".env",
        "OAUTH2_PROXY_CLIENT_ID=id\nOAUTH2_PROXY_CLIENT_SECRET=\n",
    )
    assert "oauth2-proxy" in label_only_services()


def test_oauth2_proxy_starts_when_client_is_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(
        tmp_path / "oauth2-proxy" / ".env",
        "OAUTH2_PROXY_CLIENT_ID=id\nOAUTH2_PROXY_CLIENT_SECRET=secret\n",
    )
    assert label_only_reason("oauth2-proxy") is None
    assert label_only_services() == frozenset()


def test_manage_plan_leaves_label_only_service_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "oauth2-proxy" / ".env", "OAUTH2_PROXY_CLIENT_ID=\n")
    to_up, to_down = plan_manage_changes(
        ["oauth2-proxy", "redis"],
        ["oauth2-proxy", "postgres"],
    )
    assert to_up == ["redis"]
    assert to_down == ["postgres"]
