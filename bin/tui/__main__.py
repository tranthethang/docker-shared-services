"""Launcher for the optional Textual service manager."""

from __future__ import annotations

import sys


def _require_tty() -> None:
    if sys.stdin.isatty() and sys.stdout.isatty():
        return
    print(
        "❌ The Textual service manager needs an interactive terminal (TTY).\n"
        "   Use existing non-TUI commands instead:\n"
        "     make manage   # multi-select start/stop\n"
        "     make up       # start services\n"
        "     make ps       # status\n"
        "     make logs     # logs\n"
        "     make health   # health",
        file=sys.stderr,
    )
    raise SystemExit(1)


def _require_tui_deps() -> None:
    missing: list[str] = []
    try:
        import textual  # noqa: F401
    except ImportError:
        missing.append("textual")
    try:
        import docker  # noqa: F401
    except ImportError:
        missing.append("docker")
    if not missing:
        return
    pkgs = ", ".join(missing)
    print(
        f"❌ Missing optional TUI packages: {pkgs}\n"
        "   Install with: uv sync --group tui\n"
        "   Or launch via: make tui\n"
        "   Non-TUI workflows still work: make manage, make up, make ps, …",
        file=sys.stderr,
    )
    raise SystemExit(1)


def main() -> None:
    _require_tty()
    _require_tui_deps()
    from tui.app import run_app

    run_app()


if __name__ == "__main__":
    main()
