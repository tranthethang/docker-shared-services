"""Shared password, auto-generated secrets, and legacy password rejection."""

import os
import re
import shutil
from collections.abc import Iterator
from pathlib import Path

from dss.core.config import (
    AUTO_GENERATED_SECRETS,
    INVALID_PASSWORD_VALUES,
    LEGACY_PLACEHOLDER_PASSWORD,
    SHARED_PASSWORD_KEYS,
    SHARED_PASSWORD_PLACEHOLDERS,
    SHARED_PASSWORD_TEMPLATES,
)
from dss.core.env_files import get_services
from dss.core.utils import (
    error,
    generate_hs256_jwt,
    generate_password,
    generate_secret,
    read_env_value,
    set_env_value,
    success,
    validate_password_strength,
    warning,
)

_LEGACY_DASHBOARD_HASH = "admin:$apr1$dsslocal$d6fWuAuh2eC9xV6eu7kMP."
_LEGACY_DASHBOARD_HASHES = (_LEGACY_DASHBOARD_HASH, _LEGACY_DASHBOARD_HASH.replace("$", "$$"))

# Former .env.example literals. Old .env files may still hold them; setup warns
# instead of replacing them because some (ZITADEL_MASTERKEY, REALTIME_DB_ENC_KEY)
# encrypt existing data and cannot change after first start.
KNOWN_SECRET_PLACEHOLDERS = frozenset(
    {
        "MasterkeyNeedsToHave32Characters",
        "change-me-generate-with-openssl-rand-base64-50",
        "00000000000000000000000000000000",
        "your-super-secret-jwt-token-with-at-least-32-characters-long",
        "UpNVntn3cDxHJpq99YMc1T1AQgQpc8kfYTuRgBiYa15BLrx8etQoXz3gZv1/u2oq",
        "supabaserealtime",
        "your-encryption-key-32-chars-min",
        "625729a08b95bf1b7ff351a663f3a23c",
        "850181e4652dd023b7a98c58ae0d2d34bd487ee0cc3254aed6eda37307425907",
    }
)

# Supabase API keys are JWTs whose role claim comes from the variable name.
JWT_ROLES = {"ANON_KEY": "anon", "SERVICE_ROLE_KEY": "service_role"}


def fill_secrets(service_arg: str | None) -> None:
    """Fill empty secrets and replace the former default dashboard hash."""
    services = get_services(service_arg)
    print("\nFilling empty auto-generated secrets...\n")
    filled = 0
    for s in services:
        env_path = _env_path(s)
        specs = AUTO_GENERATED_SECRETS.get(s)
        if not specs or not env_path.exists():
            continue
        for var, (method, nbytes) in specs.items():
            if _fill_secret(s, env_path, var, method, nbytes):
                filled += 1

    if filled == 0:
        print("✅ No empty auto-generated secrets to fill.")
    else:
        print(f"\n✅ Generated {filled} secret value(s).")


def _fill_secret(s: str, env_path: Path, var: str, method: str, nbytes: int) -> bool:
    """Generate one secret when it is empty. Return True when a value was written."""
    current = read_env_value(env_path, var)
    if var == "TRAEFIK_DASHBOARD_AUTH" and current and current not in _LEGACY_DASHBOARD_HASHES:
        escaped = re.sub(r"(?<!\$)\$(?!\$)", "$$", current)
        if escaped != current:
            set_env_value(env_path, var, escaped)
            success(f"{s}: escaped {var} for Docker Compose")
        else:
            success(f"{s}: {var} already set (left unchanged)")
        return False
    if current and var != "TRAEFIK_DASHBOARD_AUTH":
        if current in KNOWN_SECRET_PLACEHOLDERS:
            warning(f"{s}: {var} still holds a public placeholder (left unchanged)")
        else:
            success(f"{s}: {var} already set (left unchanged)")
        return False
    set_env_value(env_path, var, _generate_value(env_path, var, method, nbytes))
    success(f"{s}: generated {var}")
    return True


def _generate_value(env_path: Path, var: str, method: str, nbytes: int) -> str:
    if method == "htpasswd":
        shared_password = read_env_value(".env", "DSS_SHARED_PASSWORD")
        if not shared_password or shared_password in INVALID_PASSWORD_VALUES:
            error("Set a secure DSS_SHARED_PASSWORD first (run make setup).")
            raise SystemExit(1)
        return generate_secret(method, nbytes, password=shared_password)
    if method == "jwt_hs256":
        # Signed with the JWT_SECRET from the same .env; config lists it first.
        jwt_secret = read_env_value(env_path, "JWT_SECRET")
        if not jwt_secret:
            error(f"{env_path}: set JWT_SECRET before generating {var}.")
            raise SystemExit(1)
        return generate_hs256_jwt(jwt_secret, JWT_ROLES[var])
    return generate_secret(method, nbytes)


def _require_strong(password: str, source: str) -> str:
    problem = validate_password_strength(password)
    if problem:
        error(f"{source}: {problem}")
        raise SystemExit(1)
    return password


def _resolve_shared_password(explicit: str | None) -> str:
    """
    Resolve the single shared password.

    Priority:
      1. explicit --password
      2. DSS_SHARED_PASSWORD environment variable (non-empty)
      3. Existing non-placeholder DSS_SHARED_PASSWORD in root .env
      4. Fresh random password
    """
    if explicit:
        return _require_strong(explicit, "--password")
    from_env = os.environ.get("DSS_SHARED_PASSWORD", "").strip()
    if from_env:
        return _require_strong(from_env, "DSS_SHARED_PASSWORD env")
    if Path(".env").exists():
        root_existing = read_env_value(".env", "DSS_SHARED_PASSWORD")
        if root_existing and root_existing not in INVALID_PASSWORD_VALUES:
            # Existing installs keep working: data services already store this
            # password in their volumes, so never rotate it implicitly.
            problem = validate_password_strength(root_existing)
            if problem:
                warning(f"root .env DSS_SHARED_PASSWORD: {problem}")
                print(
                    "  Kept as-is. To rotate it, see 'Rotate the shared password' "
                    "in docs/troubleshooting.md.\n"
                )
            return root_existing
    return generate_password()


def _should_overwrite(current: str | None, force: bool) -> bool:
    if force:
        return True
    if current is None:
        return True
    if current in SHARED_PASSWORD_PLACEHOLDERS:
        return True
    # Compound values from old .env files that still embed the legacy placeholder.
    return LEGACY_PLACEHOLDER_PASSWORD in current


def _env_path(service: str) -> Path:
    return Path(service) / ".env"


def _announce_password_source(password: str | None) -> None:
    if password:
        success("Using password from --password")
    elif os.environ.get("DSS_SHARED_PASSWORD", "").strip():
        success("Using password from DSS_SHARED_PASSWORD env")
    elif Path(".env").exists() and read_env_value(".env", "DSS_SHARED_PASSWORD"):
        success("Reusing DSS_SHARED_PASSWORD from root .env")
    else:
        success("Generated a new random shared password")


def _apply_value(env_path: Path, key: str, value: str, dry_run: bool) -> None:
    if dry_run:
        print(f"  would set {env_path}: {key}")
    else:
        set_env_value(env_path, key, value)
        success(f"{env_path}: {key}")


def _shared_password_targets(password: str) -> Iterator[tuple[Path, str, str]]:
    """Yield (env_path, key, value) for every shared-password key whose .env exists."""
    for service, keys in SHARED_PASSWORD_KEYS.items():
        env_path = _env_path(service)
        if env_path.exists():
            for key in keys:
                yield env_path, key, password
    for (service, key), template in SHARED_PASSWORD_TEMPLATES.items():
        env_path = _env_path(service)
        if env_path.exists():
            yield env_path, key, template.format(password=password)


def fill_shared_password(
    password: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Apply ONE shared password to every SHARED_PASSWORD_KEYS entry.

    Resolution order for the password value:
      1. --password / explicit argument
      2. DSS_SHARED_PASSWORD environment variable
      3. Existing non-placeholder DSS_SHARED_PASSWORD in root .env
      4. Fresh random password (generate_password)

    By default only placeholders (empty, known change-me values, legacy default)
    are overwritten. Use force=True to rewrite all listed keys.
    """
    resolved = _resolve_shared_password(password)
    if resolved in INVALID_PASSWORD_VALUES:
        error(
            f"{LEGACY_PLACEHOLDER_PASSWORD} is an insecure placeholder; choose a secure password."
        )
        raise SystemExit(1)
    print("\nApplying shared password across services...\n")
    _announce_password_source(password)

    if dry_run:
        warning(f"Dry-run: would set shared password ({len(resolved)} chars)")
    # Ensure root .env exists so we can record DSS_SHARED_PASSWORD.
    elif not Path(".env").exists() and Path(".env.example").exists():
        shutil.copy(".env.example", ".env")
        success("Created ./.env from .env.example")

    updated = 0
    skipped = 0
    for env_path, key, value in _shared_password_targets(resolved):
        if not _should_overwrite(read_env_value(env_path, key), force):
            skipped += 1
            continue
        _apply_value(env_path, key, value, dry_run)
        updated += 1

    print(f"\n✅ Shared password sync complete (updated={updated}, skipped_custom={skipped}).")
    if not dry_run:
        warning(
            "Same password is used for all listed services. "
            "Unique secrets (Garage, Woodpecker agent, Zitadel masterkey) "
            "are handled separately by fill-secrets."
        )
        print("\nTraefik dashboard login: admin + DSS_SHARED_PASSWORD from root .env.\n")
    return resolved
