"""Check, create, and merge per-service ``.env`` files from ``.env.example``."""

import shutil
from pathlib import Path

from dss.core.config import (
    SERVICES,
)
from dss.core.utils import (
    error,
    iter_env_assignments,
    read_env_value,
    success,
    warning,
)


def get_services(service_arg: str | None) -> list[str]:
    if not service_arg or service_arg == "all":
        return ["."] + SERVICES
    if service_arg in SERVICES or service_arg == ".":
        return [service_arg]
    return []


def check_env(service_arg: str | None) -> bool:
    services = get_services(service_arg)
    print("Checking .env files...\n")
    missing: list[str] = []
    for s in services:
        env_path = Path(s) / ".env"
        example_path = Path(s) / ".env.example"
        if env_path.exists():
            success(f"{s}/.env exists")
        elif example_path.exists():
            warning(f"{s}/.env missing (only .env.example exists)")
            missing.append(s)
        else:
            error(f"{s}/.env.example not found")

    if missing:
        print(f"\nFound {len(missing)} services missing .env files")
        return True
    return False


def create_env(service_arg: str | None) -> None:
    services = get_services(service_arg)
    print("\nCreating .env files from .env.example...\n")
    created: list[str] = []
    for s in services:
        env_path = Path(s) / ".env"
        example_path = Path(s) / ".env.example"
        if example_path.exists() and not env_path.exists():
            shutil.copy(example_path, env_path)
            success(f"Created {s}/.env")
            created.append(s)
    if created:
        print("\n✅ .env files created successfully!")
    else:
        print("\n✅ No missing .env files to create.")
    warning("Next: shared password sync (fill-shared-password) + unique secrets (fill-secrets).")


def _example_env_assignments(example_path: Path) -> list[tuple[str, str]]:
    """Return (KEY, raw_value) pairs from .env.example in file order (first wins)."""
    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for key, value in iter_env_assignments(example_path):
        if key in seen:
            continue
        seen.add(key)
        pairs.append((key, value))
    return pairs


def merge_missing_env_keys(service_arg: str | None) -> None:
    """Append keys that exist in .env.example but are absent from .env.

    Never overwrites existing keys (including empty values). Safe for repeated
    `make setup` after .env.example gains new variables (e.g. AUTH_*).
    """
    services = get_services(service_arg)
    print("\nMerging missing keys from .env.example into existing .env files...\n")
    added_total = 0
    for s in services:
        env_path = Path(s) / ".env"
        example_path = Path(s) / ".env.example"
        if not env_path.exists() or not example_path.exists():
            continue
        missing = [
            (key, value)
            for key, value in _example_env_assignments(example_path)
            if read_env_value(env_path, key) is None
        ]
        if not missing:
            continue
        content = env_path.read_text()
        suffix_parts: list[str] = []
        if content and not content.endswith("\n"):
            suffix_parts.append("\n")
        if content.strip():
            suffix_parts.append("\n")
        for key, value in missing:
            suffix_parts.append(f"{key}={value}\n")
            success(f"{s}: added {key}")
            added_total += 1
        with env_path.open("a") as f:
            f.write("".join(suffix_parts))
    if added_total == 0:
        print("✅ No missing keys to merge.")
    else:
        print(f"\n✅ Added {added_total} missing key(s) from .env.example.")
