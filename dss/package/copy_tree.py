"""Copy a service directory into the package, skipping data, secrets, and escaping links."""

from __future__ import annotations

import shutil
from pathlib import Path

_SKIP_DIR_NAMES = {"data", "volumes", "__pycache__", ".venv"}


def _skip_dir(name: str) -> bool:
    return name in _SKIP_DIR_NAMES or name.endswith("_data")


def _skip_file(service: str, relative: Path) -> bool:
    if relative.name == ".env":
        return True
    return (
        service == "traefik"
        and relative.parent.as_posix() == "certs"
        and relative.suffix in {".crt", ".key"}
    )


def _link_escapes(path: Path, root: Path) -> bool:
    try:
        resolved = path.resolve(strict=False)
        resolved.relative_to(root.resolve())
    except (OSError, ValueError):
        return True
    return False


def copy_tree(src: Path, dst: Path, service: str, root: Path, relative: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for entry in src.iterdir():
        rel = relative / entry.name
        if entry.is_symlink():
            if _link_escapes(entry, root):
                continue
            (dst / entry.name).symlink_to(entry.readlink())
            continue
        if entry.is_dir():
            if _skip_dir(entry.name):
                continue
            copy_tree(entry, dst / entry.name, service, root, rel)
            continue
        if entry.is_file() and not _skip_file(service, rel):
            shutil.copy2(entry, dst / entry.name)
