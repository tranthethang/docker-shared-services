"""Service table, detail panel, and manage-selection actions for ServiceManagerApp."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.widgets import DataTable, RichLog

from dss.tui.models import ServiceStatus

_STATE_STYLES = {"running": "green", "partial": "yellow", "stopped": "red", "absent": "dim"}
_HEALTH_STYLES = {"healthy": "green", "starting": "yellow", "unhealthy": "bold red", "none": ""}

if TYPE_CHECKING:
    from dss.tui.app_base import ServiceManagerBase as _AppBase
else:
    _AppBase = object


class TableMixin(_AppBase):
    """Mixin expecting ServiceManagerApp attributes and helpers."""

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
