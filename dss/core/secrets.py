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
    generate_password,
    generate_secret,
    read_env_value,
    set_env_value,
    success,
    validate_password_strength,
    warning,
)


def fill_secrets(service_arg: str | None) -> None:
    """Fill empty secrets and replace the former default dashboard hash."""
    services = get_services(service_arg)
    print("\nFilling empty auto-generated secrets...\n")
    filled = 0
    legacy_dashboard_hash = "admin:$apr1$dsslocal$d6fWuAuh2eC9xV6eu7kMP."
    for s in services:
        env_path = _env_path(s)
        specs = AUTO_GENERATED_SECRETS.get(s)
        if not specs or not env_path.exists():
            continue
        for var, (method, nbytes) in specs.items():
            current = read_env_value(env_path, var)
            if (
                var == "TRAEFIK_DASHBOARD_AUTH"
                and current
                and current
                not in (
                    legacy_dashboard_hash,
                    legacy_dashboard_hash.replace("$", "$$"),
                )
            ):
                escaped = re.sub(r"(?<!\$)\$(?!\$)", "$$", current)
                if escaped != current:
                    set_env_value(env_path, var, escaped)
                    success(f"{s}: escaped {var} for Docker Compose")
                else:
                    success(f"{s}: {var} already set (left unchanged)")
                continue
            if current and not (
                var == "TRAEFIK_DASHBOARD_AUTH"
                and current in (legacy_dashboard_hash, legacy_dashboard_hash.replace("$", "$$"))
            ):
                success(f"{s}: {var} already set (left unchanged)")
                continue
            if method == "htpasswd":
                shared_password = read_env_value(".env", "DSS_SHARED_PASSWORD")
                if not shared_password or shared_password in INVALID_PASSWORD_VALUES:
                    error("Set a secure DSS_SHARED_PASSWORD first (run make setup).")
                    raise SystemExit(1)
                value = generate_secret(method, nbytes, password=shared_password)
            else:
                value = generate_secret(method, nbytes)
            set_env_value(env_path, var, value)
            success(f"{s}: generated {var}")
            filled += 1

    if filled == 0:
        print("✅ No empty auto-generated secrets to fill.")
    else:
        print(f"\n✅ Generated {filled} secret value(s).")


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
