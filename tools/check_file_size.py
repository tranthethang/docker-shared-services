"""Fail when a source file exceeds the line limit or grows past its baseline.

Scans ``*.py`` under bin/, scripts/, tools/, and tests/, plus every ``*.sh``
outside ``.venv``, ``dist``, ``.git``, and ``**/data``. Baselined files may
shrink but must not grow. Every other file must stay at or under the limit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

LIMIT = 300
PY_ROOTS = ("bin", "scripts", "tools", "tests")
SKIP_DIR_NAMES = {".venv", "dist", ".git", "data", "__pycache__"}
BASELINE_NAME = "file_size_baseline.json"


def line_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _skip(path: Path) -> bool:
    return any(part in SKIP_DIR_NAMES for part in path.parts)


def iter_source_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for name in PY_ROOTS:
        base = root / name
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            if _skip(path.relative_to(root)):
                continue
            found.append(path)
    for path in root.rglob("*.sh"):
        relative = path.relative_to(root)
        if _skip(relative):
            continue
        found.append(path)
    return sorted(set(found))


def load_baseline(path: Path) -> dict[str, int]:
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: baseline must be a JSON object")
    return {str(key): int(value) for key, value in data.items()}


def check_files(
    root: Path,
    baseline: dict[str, int],
    *,
    limit: int = LIMIT,
) -> list[str]:
    """Return human-readable violations. Empty means the tree is within limits."""
    problems: list[str] = []
    seen: set[str] = set()
    for path in iter_source_files(root):
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        count = line_count(path)
        if relative in baseline:
            allowed = baseline[relative]
            if count > allowed:
                problems.append(f"{relative}: {count} lines, baseline is {allowed} (file grew)")
            continue
        if count > limit:
            problems.append(f"{relative}: {count} lines exceeds limit of {limit}")
    for relative in sorted(baseline):
        if relative not in seen:
            problems.append(f"{relative}: baselined file is missing")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parents[1]
    baseline_path = root / "tools" / BASELINE_NAME
    try:
        baseline = load_baseline(baseline_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"file-size: cannot read {baseline_path}: {exc}", file=sys.stderr)
        return 1
    problems = check_files(root, baseline)
    if problems:
        print("file-size check failed:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 1
    print(f"file-size check passed ({len(iter_source_files(root))} files, limit {LIMIT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
