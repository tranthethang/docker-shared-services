"""Export a selected service stack into a runnable dist tree.

This module does not import Textual or the Docker SDK. The wizard calls
``export_stack`` only after the user confirms.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from dss.core.config import PACKAGE_REQUIRES, SERVICES
from dss.package.config_filter import filter_config_source
from dss.package.copy_tree import copy_tree
from dss.package.env_filter import filter_env_example
from dss.package.makefile_template import render_makefile
from dss.package.templates import (
    PACKAGE_GITIGNORE,
    PACKAGE_PYPROJECT,
    PACKAGE_UV_LOCK,
    render_readme,
)

_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_MAX_NAME_LENGTH = 48
# dss/ files the packaged Makefile needs: env management only.
_PACKAGE_DSS_FILES = (
    "dss/__init__.py",
    "dss/core/__init__.py",
    "dss/core/utils.py",
    "dss/core/env_files.py",
    "dss/core/secrets.py",
    "dss/core/env_report.py",
    "dss/cli/__init__.py",
    "dss/cli/env.py",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_stack_name(name: str) -> str:
    """Return ``name`` when it matches ``^[a-z][a-z0-9]*(-[a-z0-9]+)*$`` and length 1–48."""
    if (
        not isinstance(name, str)
        or not _NAME_RE.fullmatch(name)
        or not 1 <= len(name) <= _MAX_NAME_LENGTH
    ):
        raise ValueError(
            "Stack name must match ^[a-z][a-z0-9]*(-[a-z0-9]+)*$ and be 1-48 characters."
        )
    return name


def service_requires_traefik(service: str, root: Path | None = None) -> bool:
    compose = (root or repo_root()) / service / "docker-compose.yml"
    if not compose.is_file():
        return False
    return "traefik.enable=true" in compose.read_text(encoding="utf-8")


def resolve_services(selected: list[str], root: Path | None = None) -> list[str]:
    """Transitive ``PACKAGE_REQUIRES`` plus traefik, ordered as ``SERVICES``."""
    unknown = [name for name in selected if name not in SERVICES]
    if unknown:
        raise ValueError(f"Unknown services: {', '.join(unknown)}")
    if not selected:
        raise ValueError("No services selected.")

    root = root or repo_root()
    chosen = set(selected)
    changed = True
    while changed:
        changed = False
        for backend, consumers in PACKAGE_REQUIRES.items():
            if backend not in chosen and chosen.intersection(consumers):
                chosen.add(backend)
                changed = True
        if "traefik" not in chosen:
            for service in list(chosen):
                if service_requires_traefik(service, root):
                    chosen.add("traefik")
                    changed = True
                    break
    return [name for name in SERVICES if name in chosen]


def partition_selection(
    selected: list[str], root: Path | None = None
) -> tuple[list[str], list[str]]:
    """Return (checked services, dependency services added), both in ``SERVICES`` order."""
    resolved = resolve_services(selected, root)
    selected_set = set(selected)
    checked = [name for name in resolved if name in selected_set]
    added = [name for name in resolved if name not in selected_set]
    return checked, added


def export_stack(
    selected: list[str],
    name: str,
    *,
    root: Path | None = None,
    destination: Path | None = None,
) -> Path:
    """Write a runnable tree for ``selected`` services. Refuse an existing destination."""
    validate_stack_name(name)
    root = (root or repo_root()).resolve()
    services = resolve_services(selected, root)
    dest = destination if destination is not None else root / "dist" / name
    dest = dest.resolve()
    if dest.exists():
        raise FileExistsError(f"{dest} already exists")

    created = False
    try:
        dest.mkdir(parents=True)
        created = True
        for service in services:
            source = root / service
            if not source.is_dir():
                raise FileNotFoundError(f"Service directory not found: {source}")
            copy_tree(source, dest / service, service, root, Path())
        shutil.copy2(root / "docker-compose.shared.yml", dest / "docker-compose.shared.yml")
        example = (root / ".env.example").read_text(encoding="utf-8")
        (dest / ".env.example").write_text(filter_env_example(example, services), encoding="utf-8")
        for relative in _PACKAGE_DSS_FILES:
            (dest / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, dest / relative)
        config_source = (root / "dss" / "core" / "config.py").read_text(encoding="utf-8")
        (dest / "dss" / "core" / "config.py").write_text(
            filter_config_source(config_source, services), encoding="utf-8"
        )
        (dest / "Makefile").write_text(render_makefile(services), encoding="utf-8")
        (dest / "README.md").write_text(render_readme(name, services), encoding="utf-8")
        shutil.copy2(root / ".python-version", dest / ".python-version")
        (dest / "pyproject.toml").write_text(PACKAGE_PYPROJECT, encoding="utf-8")
        (dest / "uv.lock").write_text(PACKAGE_UV_LOCK, encoding="utf-8")
        (dest / ".gitignore").write_text(PACKAGE_GITIGNORE, encoding="utf-8")
    except Exception:
        if created and dest.exists():
            shutil.rmtree(dest)
        raise
    return dest
