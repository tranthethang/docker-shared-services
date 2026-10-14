"""Golden snapshots of files written by export_stack.

Regenerate with GOLDEN_UPDATE=1 (make test-update). A normal test run only compares.
"""

from __future__ import annotations

import os
from pathlib import Path

from dss.package.export import export_stack

STACKS = {
    "memcached": ["memcached"],
    "zitadel": ["zitadel"],
}
SNAPSHOTS = (
    "Makefile",
    ".env.example",
    "dss/core/config.py",
    "pyproject.toml",
    "uv.lock",
    ".gitignore",
)
# The packaged Makefile only runs env management, so only that slice of dss/ ships.
PACKAGED_DSS_FILES = [
    "dss/__init__.py",
    "dss/cli/__init__.py",
    "dss/cli/env.py",
    "dss/core/__init__.py",
    "dss/core/config.py",
    "dss/core/env_manager.py",
    "dss/core/utils.py",
]


def test_export_stack_matches_golden(repo_root: Path, tmp_path: Path) -> None:
    update = os.environ.get("GOLDEN_UPDATE") == "1"
    for name, selected in STACKS.items():
        destination = tmp_path / name
        export_stack(selected, name, root=repo_root, destination=destination)
        for relative in SNAPSHOTS:
            actual = (destination / relative).read_text(encoding="utf-8")
            golden = repo_root / "tests" / "golden" / name / relative
            if update:
                golden.parent.mkdir(parents=True, exist_ok=True)
                golden.write_text(actual, encoding="utf-8")
                continue
            assert golden.is_file(), f"missing golden {golden}; run make test-update"
            assert golden.read_text(encoding="utf-8") == actual


def test_export_ships_only_the_env_slice_of_dss(repo_root: Path, tmp_path: Path) -> None:
    destination = tmp_path / "memcached"
    export_stack(["memcached"], "memcached", root=repo_root, destination=destination)
    shipped = sorted(
        path.relative_to(destination).as_posix()
        for path in (destination / "dss").rglob("*")
        if path.is_file()
    )
    assert shipped == PACKAGED_DSS_FILES
    assert not (destination / "bin").exists()
