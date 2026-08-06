#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OLD = "infra_shared"
DEFAULT_NEW = "infra_shared"


SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
}

SKIP_FILE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".gz",
    ".tar",
    ".tgz",
    ".7z",
    ".woff",
    ".woff2",
}


@dataclass(frozen=True)
class Change:
    path: Path
    count: int


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        base = Path(dirpath)
        for name in filenames:
            p = base / name
            if p.suffix.lower() in SKIP_FILE_SUFFIXES:
                continue
            files.append(p)
    return files


def replace_in_file(path: Path, old: str, new: str, apply: bool) -> int:
    try:
        data = path.read_bytes()
    except OSError:
        return 0

    # Skip likely-binary files (contains NUL)
    if b"\x00" in data:
        return 0

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # Best-effort: skip files that aren't UTF-8 to avoid corruption.
        return 0

    if old not in text:
        return 0

    replaced = text.replace(old, new)
    if replaced == text:
        return 0

    count = text.count(old)
    if apply:
        path.write_text(replaced, encoding="utf-8")
    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bulk rename shared Docker network across this repo."
    )
    parser.add_argument("--root", default=".", help="Repo root (default: .)")
    parser.add_argument("--old", default=DEFAULT_OLD, help="Old network name")
    parser.add_argument("--new", default=DEFAULT_NEW, help="New network name")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (otherwise dry-run)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    old = args.old
    new = args.new

    changes: list[Change] = []
    total = 0
    for p in iter_files(root):
        c = replace_in_file(p, old=old, new=new, apply=args.apply)
        if c:
            changes.append(Change(path=p.relative_to(root), count=c))
            total += c

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {old} -> {new}")
    if not changes:
        print("No changes needed.")
        return 0

    for ch in sorted(changes, key=lambda x: str(x.path)):
        print(f"- {ch.path} ({ch.count})")
    print(f"Total replacements: {total}")
    if not args.apply:
        print("Re-run with --apply to write changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
