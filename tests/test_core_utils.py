"""Pin dss.core.utils: password rules, secret generation, and .env read/write."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from dss.core.utils import (
    PASSWORD_MIN_LENGTH,
    PASSWORD_SPECIALS,
    error,
    generate_password,
    generate_secret,
    print_header,
    read_env_value,
    set_env_value,
    success,
    validate_password_strength,
    warning,
)

DEFAULT_LENGTH = 32
HEX_16_BYTES = 32
BASE64_32_BYTES = 44
PLAINTEXT = "pw"


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("Short1!", "at least"),
        ("ALLUPPERCASE12345!", "lowercase"),
        ("alllowercase12345!", "uppercase"),
        ("NoDigitsAtAllHere!", "digit"),
        ("NoSpecials12345abc", "special"),
    ],
)
def test_validate_password_strength_reports_first_problem(password: str, problem: str) -> None:
    message = validate_password_strength(password)
    assert message is not None
    assert problem in message


def test_validate_password_strength_accepts_strong_password() -> None:
    assert validate_password_strength("Strong-Password-123") is None


def test_generate_password_is_strong_and_never_starts_with_special() -> None:
    for _ in range(50):
        password = generate_password()
        assert len(password) == DEFAULT_LENGTH
        assert validate_password_strength(password) is None
        assert password[0] not in PASSWORD_SPECIALS


def test_generate_password_enforces_minimum_length() -> None:
    assert len(generate_password(4)) == PASSWORD_MIN_LENGTH


def test_generate_secret_hex_and_base64() -> None:
    assert len(generate_secret("hex", 16)) == HEX_16_BYTES
    assert len(generate_secret("base64", 32)) == BASE64_32_BYTES


def test_generate_secret_rejects_unknown_method() -> None:
    with pytest.raises(ValueError, match="Unsupported secret method"):
        generate_secret("rot13")


def test_generate_secret_htpasswd_escapes_dollars(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert cmd[:3] == ["openssl", "passwd", "-apr1"]
        return subprocess.CompletedProcess(cmd, 0, stdout="$apr1$salt$hash\n", stderr="")

    monkeypatch.setattr("dss.core.utils.subprocess.run", fake_run)
    assert generate_secret("htpasswd", password=PLAINTEXT) == "admin:$$apr1$$salt$$hash"


def test_generate_secret_htpasswd_falls_back_to_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_run(*_args: object, **_kwargs: object) -> None:
        raise FileNotFoundError("openssl")

    monkeypatch.setattr("dss.core.utils.subprocess.run", failing_run)
    # base64(sha1("pw"))
    assert (
        generate_secret("htpasswd", password=PLAINTEXT) == "admin:{SHA}GpHWL3ymc5liWkNopqtdSjuqYHM="
    )


def test_read_env_value_strips_quotes_and_misses(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A='quoted'\nB=\"double\"\nC= spaced \n", encoding="utf-8")
    assert read_env_value(env_file, "A") == "quoted"
    assert read_env_value(env_file, "B") == "double"
    assert read_env_value(env_file, "C") == "spaced"
    assert read_env_value(env_file, "MISSING") is None


def test_set_env_value_replaces_in_place(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# keep\nA=1\nB=2", encoding="utf-8")
    set_env_value(env_file, "A", "9")
    assert env_file.read_text(encoding="utf-8") == "# keep\nA=9\nB=2\n"


def test_set_env_value_appends_missing_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("A=1", encoding="utf-8")
    set_env_value(str(env_file), "NEW", "x")
    assert env_file.read_text(encoding="utf-8") == "A=1\nNEW=x\n"


def test_message_helpers_prefix_output(capsys: pytest.CaptureFixture[str]) -> None:
    success("ok")
    warning("careful")
    error("broken")
    print_header("Title")
    out = capsys.readouterr().out
    assert "✅ ok" in out
    assert "⚠️  careful" in out
    assert "❌ broken" in out
    assert "Title" in out
    assert "╔" in out
