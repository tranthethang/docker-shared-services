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
    from dss.tui.app import run_app

    plan = run_app()
    if plan is None:
        return
    from dss.cli.manage import run_manage_plan

    to_up, to_down = plan
    print("")
    print("Dashboard closed. Applying manage changes (Docker output follows).")
    print("")
    run_manage_plan(to_up, to_down)


if __name__ == "__main__":
    main()
