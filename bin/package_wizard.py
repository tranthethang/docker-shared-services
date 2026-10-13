"""Textual wizard that writes a packaged stack after the user confirms."""

from __future__ import annotations

from config import PACKAGE_DEFAULT_SERVICES, SERVICES
from package_export import export_stack, partition_selection, repo_root, validate_stack_name
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Checkbox, Footer, Header, Input, Static

_DEFAULTS = set(PACKAGE_DEFAULT_SERVICES)


class SelectScreen(Screen[list[str] | None]):
    """Checkbox list in SERVICES order. Enter with nothing checked stays here."""

    BINDINGS = [
        Binding("enter", "confirm", "Continue", priority=True),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, initial: set[str] | None = None) -> None:
        super().__init__()
        self._initial = _DEFAULTS if initial is None else initial

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Space toggles a service. Enter continues.", id="select-help")
        yield Static("", id="select-error")
        with VerticalScroll(id="service-list"):
            for service in SERVICES:
                yield Checkbox(service, value=service in self._initial, id=service)
        yield Footer()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_confirm(self) -> None:
        selected = [
            service for service in SERVICES if self.query_one(f"#{service}", Checkbox).value
        ]
        if not selected:
            self.query_one("#select-error", Static).update("Select at least one service.")
            return
        self.dismiss(selected)


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
        try:
            validate_stack_name(name)
        except ValueError as exc:
            self.query_one("#name-error", Static).update(str(exc))
            return
        destination = repo_root() / "dist" / name
        if destination.exists():
            self.query_one("#name-error", Static).update(f"dist/{name}/ already exists")
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
        self._name = name
        self._checked = checked
        self._added = added

    def compose(self) -> ComposeResult:
        checked = "\n".join(f"  {service}" for service in self._checked)
        added = "\n".join(f"  {service}" for service in self._added) or "  (none)"
        yield Header()
        yield Static(
            f"Write dist/{self._name}/\n\nChecked:\n{checked}\n\n"
            f"Added for missing dependencies:\n{added}"
        )
        with Horizontal(id="confirm-actions"):
            yield Button("No", id="confirm-no")
            yield Button("Yes", id="confirm-yes", variant="primary")
        yield Footer()

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


class PackageWizard(App[None]):
    """Checkbox, name, then Yes/No. export_stack runs only after Yes."""

    TITLE = "Package stack"
    CSS = """
    Screen { padding: 0 1; }
    #select-help, #select-error, #name-error { height: auto; }
    #select-error, #name-error { color: $error; }
    #service-list { height: 1fr; border: round $primary; }
    #name-actions, #confirm-actions { height: auto; margin-top: 1; }
    Button { margin-right: 1; }
    """

    def on_mount(self) -> None:
        self.run_worker(self._flow(), exclusive=True)

    async def _flow(self) -> None:
        selected: list[str] | None = None
        while True:
            selected = await self.push_screen_wait(
                SelectScreen(set(selected) if selected else None)
            )
            if not selected:
                self.exit()
                return
            while True:
                name = await self.push_screen_wait(NameScreen())
                if name is None:
                    break
                checked, added = partition_selection(selected)
                if not await self.push_screen_wait(ConfirmScreen(name, checked, added)):
                    break
                try:
                    path = export_stack(selected, name)
                except Exception as exc:
                    await self.push_screen_wait(ErrorScreen(str(exc)))
                    continue
                self.exit(message=f"Wrote {path}")
                return


def main() -> None:
    PackageWizard().run()


if __name__ == "__main__":
    main()
