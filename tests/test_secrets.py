"""Pin shared-password resolution, sync, and auto-generated secrets in a temp tree."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path

import pytest

from dss.core.config import AUTO_GENERATED_SECRETS
from dss.core.secrets import _resolve_shared_password, fill_secrets, fill_shared_password
from dss.core.utils import JWT_LIFETIME_SECONDS, generate_hs256_jwt, read_env_value

STRONG = "Strong-Password-123"
GENERATED_LENGTH = 32
HEX_32_BYTES = 64
ZITADEL_MASTERKEY_LENGTH = 32
INNGEST_KEY_LENGTH = 16
LEGACY_DASHBOARD_HASH = "admin:$apr1$dsslocal$d6fWuAuh2eC9xV6eu7kMP."


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DSS_SHARED_PASSWORD", raising=False)
    return tmp_path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_resolve_prefers_explicit_then_env_then_root(
    tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _resolve_shared_password(STRONG) == STRONG

    monkeypatch.setenv("DSS_SHARED_PASSWORD", "From-Env-Password-1")
    assert _resolve_shared_password(None) == "From-Env-Password-1"

    monkeypatch.delenv("DSS_SHARED_PASSWORD")
    _write(tree / ".env", "DSS_SHARED_PASSWORD=Root-Env-Password-1\n")
    assert _resolve_shared_password(None) == "Root-Env-Password-1"


def test_resolve_keeps_weak_root_password_with_warning(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / ".env", "DSS_SHARED_PASSWORD=weak\n")
    assert _resolve_shared_password(None) == "weak"
    assert "Kept as-is" in capsys.readouterr().out


def test_resolve_generates_when_nothing_is_set(tree: Path) -> None:
    assert len(_resolve_shared_password(None)) == GENERATED_LENGTH


def test_resolve_rejects_weak_explicit_password(tree: Path) -> None:
    with pytest.raises(SystemExit):
        _resolve_shared_password("weak")


def test_fill_shared_password_writes_keys_and_templates(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / ".env.example", "DSS_SHARED_PASSWORD=\nCONCOURSE_ADD_LOCAL_USER=\n")
    _write(tree / "redis" / ".env", "REDIS_PASSWORD=\n")
    _write(tree / "mongodb" / ".env", "MONGO_ROOT_PASSWORD=custom-value\n")

    assert fill_shared_password(STRONG) == STRONG

    assert read_env_value(".env", "DSS_SHARED_PASSWORD") == STRONG
    assert read_env_value(".env", "CONCOURSE_ADD_LOCAL_USER") == f"admin:{STRONG}"
    assert read_env_value("redis/.env", "REDIS_PASSWORD") == STRONG
    assert read_env_value("mongodb/.env", "MONGO_ROOT_PASSWORD") == "custom-value"
    out = capsys.readouterr().out
    assert "Using password from --password" in out
    assert "Created ./.env from .env.example" in out
    assert "skipped_custom=1" in out


def test_fill_shared_password_force_overwrites_custom(tree: Path) -> None:
    _write(tree / "mongodb" / ".env", "MONGO_ROOT_PASSWORD=custom-value\n")
    fill_shared_password(STRONG, force=True)
    assert read_env_value("mongodb/.env", "MONGO_ROOT_PASSWORD") == STRONG


def test_fill_shared_password_dry_run_writes_nothing(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "redis" / ".env", "REDIS_PASSWORD=\n")
    _write(tree / "concourse" / ".env", "CONCOURSE_ADD_LOCAL_USER=\n")
    fill_shared_password(STRONG, dry_run=True)
    assert read_env_value("redis/.env", "REDIS_PASSWORD") == ""
    out = capsys.readouterr().out
    assert "would set redis/.env: REDIS_PASSWORD" in out
    assert "would set concourse/.env: CONCOURSE_ADD_LOCAL_USER" in out
    assert not (tree / ".env").exists()


@pytest.mark.parametrize(
    ("env", "root", "message"),
    [
        ("From-Env-Password-1", "", "Using password from DSS_SHARED_PASSWORD env"),
        ("", f"DSS_SHARED_PASSWORD={STRONG}\n", "Reusing DSS_SHARED_PASSWORD from root .env"),
        ("", "", "Generated a new random shared password"),
    ],
)
def test_fill_shared_password_announces_source(
    tree: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    env: str,
    root: str,
    message: str,
) -> None:
    if env:
        monkeypatch.setenv("DSS_SHARED_PASSWORD", env)
    if root:
        _write(tree / ".env", root)
    fill_shared_password(dry_run=True)
    assert message in capsys.readouterr().out


def test_fill_secrets_generates_empty_values(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "garage" / ".env", "GARAGE_RPC_SECRET=\nGARAGE_ADMIN_TOKEN=keep\n")
    fill_secrets("garage")
    rpc = read_env_value("garage/.env", "GARAGE_RPC_SECRET")
    assert rpc is not None
    assert len(rpc) == HEX_32_BYTES
    assert read_env_value("garage/.env", "GARAGE_ADMIN_TOKEN") == "keep"
    assert "Generated 1 secret value(s)" in capsys.readouterr().out

    fill_secrets("garage")
    assert "No empty auto-generated secrets to fill" in capsys.readouterr().out


def test_fill_secrets_escapes_custom_dashboard_hash(tree: Path) -> None:
    _write(tree / "traefik" / ".env", "TRAEFIK_DASHBOARD_AUTH=admin:$apr1$x$y\n")
    fill_secrets("traefik")
    assert read_env_value("traefik/.env", "TRAEFIK_DASHBOARD_AUTH") == "admin:$$apr1$$x$$y"


def test_fill_secrets_replaces_legacy_dashboard_hash(
    tree: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tree / ".env", f"DSS_SHARED_PASSWORD={STRONG}\n")
    _write(tree / "traefik" / ".env", f"TRAEFIK_DASHBOARD_AUTH={LEGACY_DASHBOARD_HASH}\n")
    monkeypatch.setattr(
        "dss.core.secrets.generate_secret",
        lambda method, _nbytes, password=None: f"{method}:{password}",
    )
    fill_secrets("traefik")
    assert read_env_value("traefik/.env", "TRAEFIK_DASHBOARD_AUTH") == f"htpasswd:{STRONG}"


def test_fill_secrets_htpasswd_needs_shared_password(tree: Path) -> None:
    _write(tree / ".env", "DSS_SHARED_PASSWORD=\n")
    _write(tree / "traefik" / ".env", "TRAEFIK_DASHBOARD_AUTH=\n")
    with pytest.raises(SystemExit):
        fill_secrets("traefik")


def _jwt_claims(token: str) -> dict[str, object]:
    payload = token.split(".")[1]
    claims: dict[str, object] = json.loads(
        base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))
    )
    return claims


def _signature_ok(token: str, secret: str) -> bool:
    signing_input, signature = token.rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256)
    encoded = base64.urlsafe_b64encode(expected.digest()).rstrip(b"=").decode("ascii")
    return hmac.compare_digest(encoded, signature)


def test_hs256_jwt_matches_signature_and_claims() -> None:
    token = generate_hs256_jwt("s3cret", "anon", now=1_000)
    assert _signature_ok(token, "s3cret")
    assert _jwt_claims(token) == {
        "role": "anon",
        "iss": "supabase",
        "iat": 1_000,
        "exp": 1_000 + JWT_LIFETIME_SECONDS,
    }


def test_fill_secrets_signs_supabase_keys_with_generated_jwt_secret(tree: Path) -> None:
    _write(tree / "supabase" / ".env", "JWT_SECRET=\nANON_KEY=\nSERVICE_ROLE_KEY=\n")
    fill_secrets("supabase")
    jwt_secret = read_env_value("supabase/.env", "JWT_SECRET")
    assert jwt_secret
    assert len(jwt_secret) == HEX_32_BYTES
    for var, role in (("ANON_KEY", "anon"), ("SERVICE_ROLE_KEY", "service_role")):
        token = read_env_value("supabase/.env", var)
        assert token
        assert _jwt_claims(token)["role"] == role
        assert _signature_ok(token, jwt_secret)


def test_fill_secrets_jwt_needs_jwt_secret(tree: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(AUTO_GENERATED_SECRETS, "supabase", {"ANON_KEY": ("jwt_hs256", 0)})
    _write(tree / "supabase" / ".env", "JWT_SECRET=\nANON_KEY=\n")
    with pytest.raises(SystemExit):
        fill_secrets("supabase")


def test_fill_secrets_warns_on_known_placeholder(
    tree: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(tree / "zitadel" / ".env", "ZITADEL_MASTERKEY=MasterkeyNeedsToHave32Characters\n")
    fill_secrets("zitadel")
    assert read_env_value("zitadel/.env", "ZITADEL_MASTERKEY") == "MasterkeyNeedsToHave32Characters"
    assert "public placeholder" in capsys.readouterr().out


def test_fill_secrets_generates_sized_values(tree: Path) -> None:
    _write(tree / "zitadel" / ".env", "ZITADEL_MASTERKEY=\n")
    _write(tree / "inngest" / ".env", "INNGEST_EVENT_KEY=\nINNGEST_SIGNING_KEY=\n")
    fill_secrets(None)
    assert (
        len(read_env_value("zitadel/.env", "ZITADEL_MASTERKEY") or "") == ZITADEL_MASTERKEY_LENGTH
    )
    for var in ("INNGEST_EVENT_KEY", "INNGEST_SIGNING_KEY"):
        value = read_env_value("inngest/.env", var) or ""
        assert len(value) == INNGEST_KEY_LENGTH
        int(value, 16)
