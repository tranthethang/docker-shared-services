"""Find the repo files to format: walk the tree, honour ignores, bucket by type."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from pathspec import PathSpec

ROOT = Path(__file__).resolve().parent.parent

ALWAYS_SKIP_DIRS = {
    ".git",
    ".venv",
    ".ruff_cache",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "__pycache__",
}

ENV_NAMES = {".env.example"}


def load_ignore_spec(root: Path) -> PathSpec:
    lines: list[str] = []
    for name in (".gitignore", ".ignore"):
        path = root / name
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)
    lines.extend(
        [
            ".git/",
            ".venv/",
            "__pycache__/",
            "uv.lock",
            "traefik/acme.json",
        ]
    )
    return PathSpec.from_lines("gitwildmatch", lines)


def is_ignored(rel: str, spec: PathSpec) -> bool:
    # Match both file and as-directory forms.
    return spec.match_file(rel) or spec.match_file(rel.rstrip("/") + "/")


def iter_repo_files(root: Path, spec: PathSpec) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        rel_dir = "" if base == root else str(base.relative_to(root)).replace("\\", "/")

        keep: list[str] = []
        for name in dirnames:
            if name in ALWAYS_SKIP_DIRS:
                continue
            child_rel = f"{rel_dir}/{name}" if rel_dir else name
            if is_ignored(child_rel, spec) or is_ignored(child_rel + "/", spec):
                continue
            keep.append(name)
        dirnames[:] = keep

        for name in filenames:
            path = base / name
            rel = str(path.relative_to(root)).replace("\\", "/")
            if is_ignored(rel, spec):
                continue
            files.append(path)
    return sorted(files)


def classify(files: Iterable[Path]) -> dict[str, list[Path]]:
    buckets: dict[str, list[Path]] = {
        "python": [],
        "yaml": [],
        "markdown": [],
        "json": [],
        "env": [],
    }
    for path in files:
        name = path.name
        suffix = path.suffix.lower()
        if suffix == ".py":
            buckets["python"].append(path)
        elif suffix in {".yml", ".yaml"}:
            buckets["yaml"].append(path)
        elif suffix == ".md":
            buckets["markdown"].append(path)
        elif suffix == ".json":
            buckets["json"].append(path)
        elif name in ENV_NAMES or (name.startswith(".env.") and name.endswith(".example")):
            buckets["env"].append(path)
    return buckets
