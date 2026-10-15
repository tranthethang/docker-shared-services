"""Pin pure env helpers without touching the repo's real .env files."""

from __future__ import annotations

from pathlib import Path

import pytest

from dss.core.config import LEGACY_PLACEHOLDER_PASSWORD, SHARED_PASSWORD_PLACEHOLDERS
from dss.core.env_files import merge_missing_env_keys
from dss.core.secrets import _should_overwrite, fill_shared_password
from dss.core.utils import iter_env_assignments


def test_iter_env_assignments_skips_comments_and_blanks(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\nFOO=bar\nBAZ=has spaces\nexport NOPE=no\n",
        encoding="utf-8",
    )
    assert list(iter_env_assignments(str(env_file))) == [("FOO", "bar"), ("BAZ", "has spaces")]


def test_merge_missing_appends_and_keeps_existing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    service = tmp_path / "memcached"
    service.mkdir()
    (service / ".env").write_text("KEEP=old\n", encoding="utf-8")
    (service / ".env.example").write_text("KEEP=new\nADDED=from-example\n", encoding="utf-8")

    merge_missing_env_keys("memcached")

    text = (service / ".env").read_text(encoding="utf-8")
    assert "KEEP=old\n" in text
    assert "ADDED=from-example\n" in text
    assert "KEEP=new" not in text


def test_shared_password_placeholder_detection() -> None:
    assert _should_overwrite(None, False) is True
    for placeholder in SHARED_PASSWORD_PLACEHOLDERS:
        assert _should_overwrite(placeholder, False) is True
    assert _should_overwrite(f"user:{LEGACY_PLACEHOLDER_PASSWORD}@db", False) is True
    assert _should_overwrite("already-set-by-the-operator", False) is False
    assert _should_overwrite("already-set-by-the-operator", True) is True


def test_legacy_password_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DSS_SHARED_PASSWORD", raising=False)
    monkeypatch.setattr(
        "dss.core.secrets._resolve_shared_password",
        lambda _explicit: LEGACY_PLACEHOLDER_PASSWORD,
    )

    with pytest.raises(SystemExit) as caught:
        fill_shared_password("unused")

    assert caught.value.code == 1
    assert "insecure placeholder" in capsys.readouterr().out
    assert not (tmp_path / ".env").exists()
