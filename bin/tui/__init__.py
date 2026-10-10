"""Optional Textual dashboard for Docker Shared Services."""

__all__ = ["main"]


def main() -> None:
    from tui.__main__ import main as _main

    _main()
