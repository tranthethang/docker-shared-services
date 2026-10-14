"""Modal screens for confirmations and help."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmScreen(ModalScreen[bool]):
    """Ask the user to confirm a destructive or bulk change."""

    # Dialogs shrink to their content and stay centered; long manage plans wrap inside max-width.
    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    #confirm-dialog {
        width: auto; min-width: 44; max-width: 80; height: auto; max-height: 80%;
        padding: 1 2; border: thick $error; background: $surface;
    }
    #confirm-title { text-style: bold; margin-bottom: 1; }
    #confirm-body { width: auto; max-width: 76; }
    #confirm-buttons { width: 100%; height: auto; margin-top: 1; align-horizontal: right; }
    #confirm-buttons Button { min-width: 14; margin-left: 1; }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Label(self._title, id="confirm-title")
            yield Static(self._body, id="confirm-body")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel (n)", variant="default", id="confirm-no")
                yield Button("Confirm (y)", variant="error", id="confirm-yes")

    def on_mount(self) -> None:
        # Default focus on Cancel so a stray Enter never applies a destructive change.
        self.query_one("#confirm-no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key == "y":
            self.dismiss(True)
        elif event.key in ("n", "escape"):
            self.dismiss(False)


class HelpScreen(ModalScreen[None]):
    DEFAULT_CSS = """
    HelpScreen { align: center middle; }
    #help-dialog {
        width: auto; height: auto; max-height: 90%;
        padding: 1 2; border: thick $primary; background: $surface;
    }
    #help-body { width: auto; }
    #help-close { margin-top: 1; }
    """

    HELP = """\
Keyboard controls

  ↑/↓ / j/k     Move selection
  /             Focus filter (Enter/Esc returns to the list)
  r             Force status refresh (auto-updates on Docker events)
  Enter         Show container details (also follow the cursor)
  l             Follow live logs / stop following
  u             Up (start) selected service
  d             Down (confirm) selected service
  s             Stop selected service
  Shift+R       Restart selected service
  Space         Toggle manage selection
  m             Apply manage plan (confirm)
  a             Select all for manage
  c             Clear manage selection
  ?             This help
  q             Quit

Existing Makefile/CLI workflows are unchanged
(make manage, make up, make ps, …).
"""

    def compose(self) -> ComposeResult:
        with Vertical(id="help-dialog"):
            yield Static(self.HELP, id="help-body")
            yield Button("Close", id="help-close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "help-close":
            self.dismiss(None)

    def on_key(self, event) -> None:  # type: ignore[no-untyped-def]
        if event.key in ("escape", "q", "enter"):
            self.dismiss(None)
