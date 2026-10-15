"""Interactive checkbox menu: arrow keys navigate, space toggles, enter confirms."""

import sys
import termios
import tty
from collections.abc import Callable

_ARROW_KEYS = {"A": "UP", "B": "DOWN"}
_PLAIN_KEYS = {"\r": "ENTER", "\n": "ENTER", " ": "SPACE", "\x03": "CTRL_C", "q": "Q", "Q": "Q"}


def _read_key() -> str:
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            if sys.stdin.read(1) == "[":
                key = _ARROW_KEYS.get(sys.stdin.read(1))
                if key:
                    return key
            return "ESC"
        return _PLAIN_KEYS.get(ch, "OTHER")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _enter_alt_screen() -> None:
    sys.stdout.write("\033[?1049h\033[H\033[?25l")
    sys.stdout.flush()


def _leave_alt_screen() -> None:
    sys.stdout.write("\033[?25h\033[?1049l")
    sys.stdout.flush()


def _render(
    title: str,
    items: list[str],
    selected: set[str],
    cursor: int,
    badge_fn: Callable[[str], str] | None,
) -> None:
    width = 66
    lines = [
        "",
        "╔" + "═" * (width - 2) + "╗",
        f"║ {title:^{width - 4}} ║",
        "╚" + "═" * (width - 2) + "╝",
        "",
        "  ↑/↓ navigate   Space toggle   Enter confirm   Esc cancel",
        "",
    ]

    name_width = max((len(item) for item in items), default=0) + 2

    for i, item in enumerate(items):
        check = "x" if item in selected else " "
        badge = badge_fn(item) if badge_fn else ""
        prefix = ">" if i == cursor else " "
        line = f" {prefix} {item:<{name_width}} [{check}]{badge}"
        if i == cursor:
            line = f"\033[7m{line:<{width - 2}}\033[0m"
        lines.append(line)

    sys.stdout.write("\033[H\033[J" + "\n".join(lines))
    sys.stdout.flush()


def _toggle(selected: set[str], item: str) -> None:
    if item in selected:
        selected.discard(item)
    else:
        selected.add(item)


def show_checkbox_menu(
    items: list[str],
    default_checked: list[str] | None = None,
    title: str = "Select",
    badge_fn: Callable[[str], str] | None = None,
) -> list[str] | None:
    """
    Show an interactive checkbox menu.
    Returns sorted list of selected items, or None when TTY is unavailable.
    """
    if default_checked is None:
        default_checked = []

    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    selected = set(default_checked)
    cursor = 0

    _enter_alt_screen()
    try:
        while True:
            _render(title, items, selected, cursor, badge_fn)
            key = _read_key()

            if key == "UP":
                cursor = (cursor - 1) % len(items)
            elif key == "DOWN":
                cursor = (cursor + 1) % len(items)
            elif key == "SPACE":
                _toggle(selected, items[cursor])
            elif key == "ENTER":
                _leave_alt_screen()
                return sorted(selected, key=items.index)
            elif key in ("ESC", "Q", "CTRL_C"):
                _leave_alt_screen()
                sys.exit(0)
    except KeyboardInterrupt:
        _leave_alt_screen()
        sys.exit(0)
