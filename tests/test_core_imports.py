"""dss.core is the layer the exporter copies, so it must stay standard-library only."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


def _imported_roots(path: Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_core_imports_only_stdlib_and_core(repo_root: Path) -> None:
    allowed = set(sys.stdlib_module_names) | {"__future__"}
    problems: list[str] = []
    for path in sorted((repo_root / "dss" / "core").rglob("*.py")):
        for root in sorted(_imported_roots(path) - allowed):
            if root == "dss":
                continue  # import-linter checks which dss layers core may use.
            problems.append(f"{path.relative_to(repo_root)} imports {root}")
    assert problems == []
