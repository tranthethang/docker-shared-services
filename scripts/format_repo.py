#!/usr/bin/env python3
"""Format repo config files: Python, YAML, Markdown, JSON, and .env.example.

Respects .gitignore and .ignore (gitwildmatch). Run via:

    uv run python scripts/format_repo.py
    uv run python scripts/format_repo.py --check
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
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


@dataclass
class Stats:
    changed: list[str] = field(default_factory=list)
    checked: int = 0
    errors: list[str] = field(default_factory=list)

    def note(self, path: Path, *, changed: bool) -> None:
        self.checked += 1
        if changed:
            self.changed.append(str(path.relative_to(ROOT)))


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


def run_cmd(cmd: list[str], *, check_mode: bool) -> int:
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0 and not check_mode:
        return result.returncode
    return result.returncode


def format_python(paths: list[Path], *, check: bool) -> int:
    if not paths:
        return 0
    print(f"Python ({len(paths)} files)")
    args = ["ruff", "format"]
    if check:
        args.append("--check")
    args.extend(str(p) for p in paths)
    code = run_cmd(args, check_mode=check)
    # Apply safe autofixes when writing (imports, etc.)
    if not check:
        lint = ["ruff", "check", "--fix", "--quiet", *[str(p) for p in paths]]
        run_cmd(lint, check_mode=False)
    return code


def format_yaml(paths: list[Path], *, check: bool) -> int:
    if not paths:
        return 0
    print(f"YAML ({len(paths)} files)")
    args = ["yamlfix"]
    if check:
        args.append("--check")
    args.extend(str(p) for p in paths)
    return run_cmd(args, check_mode=check)


def format_markdown(paths: list[Path], *, check: bool) -> int:
    if not paths:
        return 0
    print(f"Markdown ({len(paths)} files)")
    args = ["mdformat", "--wrap", "keep", "--end-of-line", "lf"]
    if check:
        args.append("--check")
    args.extend(str(p) for p in paths)
    return run_cmd(args, check_mode=check)


def format_json_file(path: Path, *, check: bool, stats: Stats) -> int:
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        stats.errors.append(f"{path.relative_to(ROOT)}: invalid JSON ({exc})")
        return 1
    formatted = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    changed = raw != formatted
    stats.note(path, changed=changed)
    if changed and not check:
        path.write_text(formatted, encoding="utf-8", newline="\n")
    if changed and check:
        return 1
    return 0


def format_json(paths: list[Path], *, check: bool, stats: Stats) -> int:
    if not paths:
        return 0
    print(f"JSON ({len(paths)} files)")
    code = 0
    for path in paths:
        code |= format_json_file(path, check=check, stats=stats)
    return code


def format_env_text(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    cleaned = [line.rstrip() for line in lines]
    # Drop trailing empty lines, then ensure a single trailing newline.
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return "\n".join(cleaned) + "\n"


def format_env_file(path: Path, *, check: bool, stats: Stats) -> int:
    raw = path.read_text(encoding="utf-8")
    formatted = format_env_text(raw)
    changed = raw != formatted
    stats.note(path, changed=changed)
    if changed and not check:
        path.write_text(formatted, encoding="utf-8", newline="\n")
    if changed and check:
        return 1
    return 0


def format_env(paths: list[Path], *, check: bool, stats: Stats) -> int:
    if not paths:
        return 0
    print(f".env.example ({len(paths)} files)")
    code = 0
    for path in paths:
        code |= format_env_file(path, check=check, stats=stats)
    return code


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check formatting without writing files",
    )
    parser.add_argument(
        "--types",
        default="all",
        help="Comma-separated types: python,yaml,markdown,json,env,all (default: all)",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Optional paths to limit formatting (default: whole repo)",
    )
    return parser.parse_args(argv)


def parse_types(raw: str) -> set[str]:
    allowed = {"python", "yaml", "markdown", "json", "env", "all"}
    parts = {p.strip().lower() for p in raw.split(",") if p.strip()}
    if not parts:
        parts = {"all"}
    unknown = parts - allowed
    if unknown:
        raise SystemExit(f"Unknown --types: {', '.join(sorted(unknown))}")
    if "all" in parts:
        return {"python", "yaml", "markdown", "json", "env"}
    return parts


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)

    args = parse_args(argv)
    wanted = parse_types(args.types)
    spec = load_ignore_spec(ROOT)

    if args.paths:
        selected: list[Path] = []
        for raw in args.paths:
            path = raw if raw.is_absolute() else (ROOT / raw)
            path = path.resolve()
            if path.is_dir():
                selected.extend(iter_repo_files(path, spec))
            elif path.is_file():
                rel = str(path.relative_to(ROOT)).replace("\\", "/")
                if not is_ignored(rel, spec):
                    selected.append(path)
        files = sorted(set(selected))
    else:
        files = iter_repo_files(ROOT, spec)

    buckets = classify(files)

    print(f"Root: {ROOT}", flush=True)
    print(f"Mode: {'check' if args.check else 'write'}", flush=True)
    print(flush=True)

    stats = Stats()
    exit_code = 0

    if "python" in wanted:
        exit_code |= format_python(buckets["python"], check=args.check)
    if "yaml" in wanted:
        exit_code |= format_yaml(buckets["yaml"], check=args.check)
    if "markdown" in wanted:
        exit_code |= format_markdown(buckets["markdown"], check=args.check)
    if "json" in wanted:
        exit_code |= format_json(buckets["json"], check=args.check, stats=stats)
    if "env" in wanted:
        exit_code |= format_env(buckets["env"], check=args.check, stats=stats)

    if stats.errors:
        print()
        print("Errors:")
        for err in stats.errors:
            print(f"  - {err}")
        exit_code |= 1

    if stats.changed:
        print()
        label = "Would reformat" if args.check else "Reformatted"
        print(f"{label} ({len(stats.changed)}):")
        for item in stats.changed:
            print(f"  - {item}")

    print()
    if exit_code == 0:
        print("✅ Format OK" if args.check else "✅ Format complete")
    else:
        print("❌ Format issues found" if args.check else "❌ Format finished with errors")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
