"""Stack name, confirmation, and error screens of the package wizard."""

from __future__ import annotations

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, Static

from dss.package.wizard_model import confirm_rows, stack_name_error


class NameScreen(Screen[str | None]):
    """Accept a stack name, or stay put when it is invalid or already exported."""

    BINDINGS = [Binding("escape", "back", "Back")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Stack name: lowercase letters, digits, and hyphens, 1-48 characters.")
        yield Input(placeholder="my-stack", id="stack-name")
        yield Static("", id="name-error")
        with Horizontal(id="name-actions"):
            yield Button("Back", id="name-back")
            yield Button("Continue", id="name-continue", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#stack-name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit(event.value)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "name-back":
            self.dismiss(None)
            return
        self._submit(self.query_one("#stack-name", Input).value)

    def action_back(self) -> None:
        self.dismiss(None)

    def _submit(self, raw: str) -> None:
        name = raw.strip()
        problem = stack_name_error(name)
        if problem is not None:
            self.query_one("#name-error", Static).update(problem)
            return
        self.dismiss(name)


class ConfirmScreen(Screen[bool]):
    """Yes writes the tree. No returns to the service list."""

    BINDINGS = [
        Binding("y", "yes", "Yes"),
        Binding("n", "no", "No", priority=True),
        Binding("enter", "yes", "Yes", priority=True),
    ]

    def __init__(self, name: str, checked: list[str], added: list[str]) -> None:
        super().__init__()
        self._stack_name = name
        self._checked = checked
        self._added = added

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(
            f"Write dist/{escape(self._stack_name)}/ with {len(self._checked) + len(self._added)} "
            f"services ({len(self._checked)} checked, {len(self._added)} added as dependencies).",
            id="confirm-title",
        )
        yield DataTable(id="confirm-table", cursor_type="none", zebra_stripes=True)
        with Horizontal(id="confirm-actions"):
            yield Button("No", id="confirm-no")
            yield Button("Yes", id="confirm-yes", variant="primary")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#confirm-table", DataTable)
        table.add_columns("Service", "Category", "Web UI", "Reason")
        for row in confirm_rows(self._checked, self._added):
            table.add_row(*row)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-yes")

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class ErrorScreen(Screen[None]):
    BINDINGS = [Binding("enter", "close", "Close", priority=True)]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self._message)
        yield Button("Close", id="error-close")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
