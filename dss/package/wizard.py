"""Textual wizard that writes a packaged stack after the user confirms."""

from __future__ import annotations

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from dss.package.export import export_stack, partition_selection
from dss.package.wizard_model import (
    CATALOG,
    DEFAULTS,
    MARKS,
    STATE_LABELS,
    added_dependencies,
    grouped_matches,
    ordered_selection,
    required_by,
    requires,
    selection_state,
    toggle,
)
from dss.package.wizard_screens import ConfirmScreen, ErrorScreen, NameScreen


class SelectScreen(Screen[list[str] | None]):
    """Services grouped by category, with a filter and a detail panel.

    Enter with nothing checked stays here.
    """

    BINDINGS = [
        Binding("enter", "confirm", "Continue", priority=True),
        Binding("space", "toggle_service", "Toggle"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("q", "cancel", "Quit"),
    ]

    def __init__(self, initial: set[str] | None = None) -> None:
        super().__init__()
        self._checked = set(DEFAULTS if initial is None else initial)
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
        self._added = added_dependencies(self._checked)

    def _prompt(self, service: str) -> str:
        mark = MARKS[selection_state(service, self._checked, self._added)]
        web = " 🌐" if CATALOG[service]["web_ui"] else ""
        auto = "  [dim]auto[/dim]" if service in self._added else ""
        return f"{escape(mark)} {service}{web}{auto}"

    def _rebuild(self) -> None:
        option_list = self.query_one("#service-list", OptionList)
        highlighted = self._highlighted_service()
        options: list[Option] = []
        for category, members in grouped_matches(self._query):
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
        entry = CATALOG[service]
        needs = ", ".join(requires(service)) or "—"
        users = ", ".join(required_by(service)) or "—"
        web_ui = "\n".join(f"  {escape(url)}" for url in entry["web_ui"]) or "  —"
        state = STATE_LABELS[selection_state(service, self._checked, self._added)]
        detail.update(
            f"[b]{escape(service)}[/b]  [dim]{escape(entry['category'])}[/dim]\n"
            f"{escape(entry['description'])}\n\n"
            f"[b]Status[/b]       {state}\n"
            f"[b]Containers[/b]   {escape(', '.join(entry['containers']))}\n"
            f"[b]Requires[/b]     {escape(needs)}\n"
            f"[b]Required by[/b]  {escape(users)}\n"
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

    def action_toggle_service(self) -> None:
        service = self._highlighted_service()
        if service:
            self._toggle(service)

    def _toggle(self, service: str) -> None:
        self._checked = toggle(self._checked, service)
        self._recompute()
        self._refresh_prompts()
        self._show_detail(service)

    def action_cancel(self) -> None:
        self.dismiss(None)

    def action_confirm(self) -> None:
        selected = ordered_selection(self._checked)
        if not selected:
            self.query_one("#select-status", Static).update(
                "[b red]Select at least one service.[/b red]"
            )
            return
        self.dismiss(selected)


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
