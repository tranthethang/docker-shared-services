"""Textual wizard that writes a packaged stack after the user confirms."""

from __future__ import annotations

from config import PACKAGE_DEFAULT_SERVICES, PACKAGE_REQUIRES, SERVICES, direct_dependencies
from package_export import (
    export_stack,
    partition_selection,
    repo_root,
    service_requires_traefik,
    validate_stack_name,
)
from rich.markup import escape
from service_catalog import CATEGORIES, load_catalog
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

_DEFAULTS = set(PACKAGE_DEFAULT_SERVICES)
_CATALOG = load_catalog()
_TRAEFIK_USERS = [name for name in SERVICES if name != "traefik" and service_requires_traefik(name)]


def _requires(service: str) -> list[str]:
    needs = direct_dependencies(service)
    if service != "traefik" and service in _TRAEFIK_USERS:
        needs = ["traefik", *needs]
    return [name for name in SERVICES if name in needs]


def _required_by(service: str) -> list[str]:
    users = set(PACKAGE_REQUIRES.get(service, []))
    if service == "traefik":
        users.update(_TRAEFIK_USERS)
    return [name for name in SERVICES if name in users]


def _matches(service: str, query: str) -> bool:
    if not query:
        return True
    entry = _CATALOG[service]
    haystack = f"{service} {entry['category']} {entry['description']}".lower()
    return query.lower() in haystack


class SelectScreen(Screen[list[str] | None]):
    """Services grouped by category, with a filter and a detail panel.

    Enter with nothing checked stays here.
    """

    BINDINGS = [
        Binding("enter", "confirm", "Continue", priority=True),
        Binding("space", "toggle", "Toggle"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, initial: set[str] | None = None) -> None:
        super().__init__()
        self._checked = set(_DEFAULTS if initial is None else initial)
        self._added: set[str] = set()
        self._query = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Filter by name, category, or description", id="select-filter")
        yield Static("", id="select-status")
        with Horizontal(id="select-body"):
            yield OptionList(id="service-list")
            with VerticalScroll(id="service-detail"):
                yield Static("", id="detail-text")
        yield Footer()

    def on_mount(self) -> None:
        self._recompute()
        self._rebuild()
        self.query_one("#service-list", OptionList).focus()

    def _recompute(self) -> None:
        if self._checked:
            _checked, added = partition_selection(sorted(self._checked))
            self._added = set(added)
        else:
            self._added = set()

    def _prompt(self, service: str) -> str:
        if service in self._checked:
            mark = "[x]"
        elif service in self._added:
            mark = "[+]"
        else:
            mark = "[ ]"
        web = " 🌐" if _CATALOG[service]["web_ui"] else ""
        auto = "  [dim]auto[/dim]" if service in self._added else ""
        return f"{escape(mark)} {service}{web}{auto}"

    def _rebuild(self) -> None:
        option_list = self.query_one("#service-list", OptionList)
        highlighted = self._highlighted_service()
        options: list[Option] = []
        for category in CATEGORIES:
            members = [
                name
                for name in SERVICES
                if _CATALOG[name]["category"] == category and _matches(name, self._query)
            ]
            if not members:
                continue
            options.append(Option(f"[b]{escape(category)}[/b]", disabled=True))
            options.extend(Option(self._prompt(name), id=name) for name in members)
        option_list.set_options(options)
        if not any(option.id for option in options):
            self._show_detail(None)
        else:
            target = highlighted
            if target is None or not any(option.id == target for option in options):
                target = next(option.id for option in options if option.id)
            option_list.highlighted = option_list.get_option_index(target)
            # The highlight event does not fire when the index is unchanged.
            self._show_detail(target)
        self._update_status()

    def _refresh_prompts(self) -> None:
        option_list = self.query_one("#service-list", OptionList)
        for index in range(option_list.option_count):
            option = option_list.get_option_at_index(index)
            if option.id:
                option_list.replace_option_prompt(option.id, self._prompt(option.id))
        self._update_status()

    def _update_status(self) -> None:
        text = f"{len(self._checked)} checked · +{len(self._added)} dependencies"
        if self._query:
            text += f" · filter: {escape(self._query)}"
        self.query_one("#select-status", Static).update(text)

    def _highlighted_service(self) -> str | None:
        option_list = self.query_one("#service-list", OptionList)
        if option_list.highlighted is None or option_list.option_count == 0:
            return None
        return option_list.get_option_at_index(option_list.highlighted).id

    def _show_detail(self, service: str | None) -> None:
        detail = self.query_one("#detail-text", Static)
        if service is None:
            detail.update("No service matches the filter.")
            return
        entry = _CATALOG[service]
        requires = ", ".join(_requires(service)) or "—"
        required_by = ", ".join(_required_by(service)) or "—"
        web_ui = "\n".join(f"  {escape(url)}" for url in entry["web_ui"]) or "  —"
        if service in self._checked:
            state = "checked"
        elif service in self._added:
            state = "added as a dependency"
        else:
            state = "not selected"
        detail.update(
            f"[b]{escape(service)}[/b]  [dim]{escape(entry['category'])}[/dim]\n"
            f"{escape(entry['description'])}\n\n"
            f"[b]Status[/b]       {state}\n"
            f"[b]Containers[/b]   {escape(', '.join(entry['containers']))}\n"
            f"[b]Requires[/b]     {escape(requires)}\n"
            f"[b]Required by[/b]  {escape(required_by)}\n"
            f"[b]Web UI[/b]\n{web_ui}"
        )

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option.id:
            self._show_detail(event.option.id)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # Mouse click on a row toggles it, like Space.
        if event.option.id:
            self._toggle(event.option.id)

    def on_input_changed(self, event: Input.Changed) -> None:
        self._query = event.value.strip()
        self._rebuild()

    def action_focus_filter(self) -> None:
        self.query_one("#select-filter", Input).focus()

    def action_toggle(self) -> None:
        service = self._highlighted_service()
        if service:
            self._toggle(service)

    def _toggle(self, service: str) -> None:
        if service in self._checked:
            self._checked.discard(service)
        else:
            # Toggling an auto-added dependency makes it an explicit choice.
            self._checked.add(service)
        self._recompute()
        self._refresh_prompts()
        self._show_detail(service)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_confirm(self) -> None:
        selected = [service for service in SERVICES if service in self._checked]
        if not selected:
            self.query_one("#select-status", Static).update(
                "[b red]Select at least one service.[/b red]"
            )
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
        yield Header()
        yield Static(
            f"Write dist/{escape(self._name)}/ with {len(self._checked) + len(self._added)} "
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
        checked = set(self._checked)
        for service in SERVICES:
            if service not in checked and service not in self._added:
                continue
            entry = _CATALOG[service]
            web_ui = entry["web_ui"][0] if entry["web_ui"] else "—"
            reason = "checked" if service in checked else "dependency"
            table.add_row(service, entry["category"], web_ui, reason)

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
    """Service list, name, then Yes/No. export_stack runs only after Yes."""

    TITLE = "Package stack"
    CSS = """
    Screen { padding: 0 1; }
    #select-status, #name-error, #confirm-title { height: auto; margin: 0 0 1 0; }
    #name-error { color: $error; }
    #select-body { height: 1fr; }
    #service-list { width: 2fr; height: 1fr; border: round $primary; }
    #service-detail { width: 3fr; height: 1fr; border: round $secondary; padding: 0 1; }
    #confirm-table { height: 1fr; }
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
