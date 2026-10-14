"""Golden snapshots of files written by export_stack.

Regenerate with GOLDEN_UPDATE=1 (make test-update). A normal test run only compares.
"""

from __future__ import annotations

import os
from pathlib import Path

from package_export import export_stack

STACKS = {
    "memcached": ["memcached"],
    "zitadel": ["zitadel"],
}
SNAPSHOTS = (
    "Makefile",
    ".env.example",
    "bin/config.py",
    "pyproject.toml",
    ".gitignore",
)


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
