"""Textual dashboard for Docker Shared Services."""

from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, RichLog, Static
from tui.docker_state import (
    DockerStateError,
    EventWatcher,
    LogFollower,
    connect_client,
    list_service_statuses,
)
from tui.models import ServiceStatus
from tui.ops_mixin import OpsMixin
from tui.screens import HelpScreen

LOG_MAX_LINES = 2000
EVENT_DEBOUNCE_SECONDS = 0.3

_STATE_STYLES = {"running": "green", "partial": "yellow", "stopped": "red", "absent": "dim"}
_HEALTH_STYLES = {"healthy": "green", "starting": "yellow", "unhealthy": "bold red", "none": ""}


class ServiceManagerApp(OpsMixin, App[None]):
    TITLE = "Docker Shared Services"
    # Header/Footer are docked; everything else flows top-to-bottom so nothing overlaps.
    # The table is sized to its columns; the side panel takes the remaining width for logs.
    CSS = """
    #filter { height: 1; border: none; padding: 0 1; background: $boost; }
    #filter:focus { background: $accent 30%; }
    #main { height: 1fr; }
    #table { width: auto; min-width: 44; max-width: 50%; height: 1fr; }
    #side { width: 1fr; height: 1fr; }
    #detail { height: 1fr; border: round $primary; border-title-color: $text; }
    #ops {
        height: auto; min-height: 3; max-height: 10;
        border: round $accent; border-title-color: $text;
    }
    #status { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("question_mark", "help", "Help"),
        Binding("r", "refresh", "Refresh"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("escape", "focus_table", "Back", show=False),
        Binding("u", "op_up", "Up"),
        Binding("d", "op_down", "Down"),
        Binding("s", "op_stop", "Stop"),
        Binding("shift+r", "op_restart", "Restart"),
        Binding("l", "load_logs", "Logs"),
        Binding("space", "toggle_manage", "Toggle", show=False),
        Binding("m", "apply_manage", "Manage"),
        Binding("a", "select_all_manage", "All", show=False),
        Binding("c", "clear_manage", "Clear", show=False),
        Binding("enter", "show_detail", "Detail", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[ServiceStatus] = []
        self._filter = ""
        self._manage: set[str] = set()
        self._manage_initialized = False
        self._manage_dirty = False
        self._busy = False
        self._status_refreshing = False
        self._log_target: str | None = None
        self._log_follower: LogFollower | None = None
        self._log_resume_since: int | None = None
        self._event_watcher: EventWatcher | None = None
        self._event_refresh_pending = False
        self._refresh_again = False
        self._docker_error = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="/ Filter services…  (Enter/Esc returns to the list)", id="filter")
        with Horizontal(id="main"):
            yield DataTable(id="table", cursor_type="row")
            with Vertical(id="side"):
                yield RichLog(
                    id="detail", highlight=False, markup=False, wrap=True, max_lines=LOG_MAX_LINES
                )
                yield RichLog(id="ops", highlight=False, markup=False)
        yield Static("Ready", id="status")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#table", DataTable)
        table.add_columns("✓", "Service", "State", "Health", "Ctrs")
        table.focus()
        self.query_one("#detail", RichLog).border_title = "Details"
        self.query_one("#ops", RichLog).border_title = "Operations"
        self._start_refresh()
        self.set_interval(0.2, self._drain_logs)
        self._event_watcher = EventWatcher(self._on_docker_event)
        self._event_watcher.start()

    def on_unmount(self) -> None:
        if self._event_watcher is not None:
            self._event_watcher.stop()
        self._stop_logs()

    def _on_docker_event(self) -> None:
        """Called from the event thread; coalesce bursts (e.g. `compose up` of a stack)."""
        try:
            self.call_from_thread(self._schedule_event_refresh)
        except RuntimeError:
            pass  # app is shutting down

    def _schedule_event_refresh(self) -> None:
        if self._event_refresh_pending:
            return
        self._event_refresh_pending = True
        self.set_timer(EVENT_DEBOUNCE_SECONDS, self._event_refresh)

    def _event_refresh(self) -> None:
        self._event_refresh_pending = False
        self._start_refresh()

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _ops_log(self, message: str) -> None:
        self.query_one("#ops", RichLog).write(message)

    def _detail_clear(self) -> None:
        self.query_one("#detail", RichLog).clear()

    def _detail_write(self, message: str) -> None:
        self.query_one("#detail", RichLog).write(message)

    def _start_refresh(self) -> None:
        if self._status_refreshing:
            # Re-run once the current refresh lands so a late event is never lost.
            self._refresh_again = True
            return
        self._status_refreshing = True
        self._set_status("Refreshing service status…")
        self.run_worker(self._refresh_worker, exclusive=False, thread=True)

    def _refresh_worker(self) -> None:
        client = None
        try:
            client = connect_client()
            rows = list_service_statuses(client)
            self.call_from_thread(self._apply_refresh, rows)
        except DockerStateError as exc:
            self.call_from_thread(self._apply_refresh_error, str(exc))
        except Exception as exc:
            self.call_from_thread(self._apply_refresh_error, f"Docker refresh failed: {exc}")
        finally:
            if client is not None:
                client.close()

    def _apply_refresh(self, rows: list[ServiceStatus]) -> None:
        self._status_refreshing = False
        self._docker_error = ""
        self._rows = rows
        if not self._manage_initialized or not self._manage_dirty:
            self._manage = {row.name for row in rows if row.running_count > 0}
            self._manage_initialized = True
        self._render_table()
        if not self._busy and self._log_follower is None:
            self._set_status(f"Loaded {len(rows)} services")
        self._resume_logs_after_refresh()
        self._finish_refresh_cycle()

    def _finish_refresh_cycle(self) -> None:
        if self._refresh_again:
            self._refresh_again = False
            self._start_refresh()

    def _apply_refresh_error(self, message: str) -> None:
        self._status_refreshing = False
        self._docker_error = message
        self._rows = []
        self._render_table()
        self._set_status(message)
        self._ops_log(message)
        self._finish_refresh_cycle()

    def _filtered_rows(self) -> list[ServiceStatus]:
        needle = self._filter.strip().lower()
        if not needle:
            return self._rows
        return [r for r in self._rows if needle in r.name.lower()]

    def _render_table(self) -> None:
        table = self.query_one("#table", DataTable)
        selected = self._selected_service()
        rows = self._filtered_rows()
        table.clear()
        for row in rows:
            mark = Text("✓", style="bold green") if row.name in self._manage else ""
            containers = f"{row.running_count}/{row.container_count}"
            table.add_row(
                mark,
                row.name,
                Text(row.state, style=_STATE_STYLES.get(row.state, "")),
                Text(row.health, style=_HEALTH_STYLES.get(row.health, "dim")),
                containers,
                key=row.name,
            )
        if selected:
            for index, row in enumerate(rows):
                if row.name == selected:
                    table.move_cursor(row=index)
                    break

    def _selected_service(self) -> str | None:
        table = self.query_one("#table", DataTable)
        if table.row_count == 0:
            return None
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        if row_key is None:
            return None
        return str(row_key.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "filter":
            return
        self._filter = event.value
        self._render_table()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter":
            self.action_focus_table()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        # Details follow the cursor unless a log view is active.
        if self._log_target is None and event.row_key is not None:
            self._render_detail(str(event.row_key.value))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        # DataTable owns Enter, so the app-level Enter binding never fires while it has focus.
        self.action_show_detail()

    def action_focus_filter(self) -> None:
        self.query_one("#filter", Input).focus()

    def action_focus_table(self) -> None:
        self.query_one("#table", DataTable).focus()

    def action_refresh(self) -> None:
        if self._busy:
            self._set_status("Busy — wait for the current operation")
            return
        self._start_refresh()

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_cursor_down(self) -> None:
        self.query_one("#table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#table", DataTable).action_cursor_up()

    def action_show_detail(self) -> None:
        self._stop_logs()
        name = self._selected_service()
        if name:
            self._render_detail(name)

    def _render_detail(self, name: str) -> None:
        row = next((r for r in self._rows if r.name == name), None)
        self.query_one("#detail", RichLog).border_title = f"Details · {name}"
        self._detail_clear()
        if row is None:
            self._detail_write(f"No data for {name}")
            return
        self._detail_write(f"Service: {row.name}")
        self._detail_write(f"State: {row.state}  Health: {row.health}")
        self._detail_write(f"Containers: {row.running_count}/{row.container_count}")
        if not row.containers:
            self._detail_write("(no containers — stack absent)")
            return
        for c in row.containers:
            self._detail_write(
                f"- {c.name}  [{c.compose_service}]  {c.status}/{c.health}  {c.image}"
            )

    def action_toggle_manage(self) -> None:
        name = self._selected_service()
        if not name:
            return
        if name in self._manage:
            self._manage.discard(name)
        else:
            self._manage.add(name)
        self._manage_dirty = True
        self._render_table()
        self._set_status(f"Manage selection: {len(self._manage)} service(s)")

    def action_select_all_manage(self) -> None:
        self._manage = {r.name for r in self._filtered_rows()}
        self._manage_dirty = True
        self._render_table()

    def action_clear_manage(self) -> None:
        self._manage.clear()
        self._manage_dirty = True
        self._render_table()


def run_app() -> None:
    ServiceManagerApp().run()
