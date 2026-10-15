"""Typing-only view of ServiceManagerApp, shared by its mixins.

The mixins import this under ``TYPE_CHECKING`` only, so at runtime they stay plain
``object`` subclasses. ``ServiceManagerApp`` provides every attribute and method here.
"""

from __future__ import annotations

from textual.app import App

from dss.tui.docker_state import LogFollower
from dss.tui.models import ServiceStatus


class ServiceManagerBase(App[None]):
    _rows: list[ServiceStatus]
    _filter: str
    _manage: set[str]
    _manage_dirty: bool
    _busy: bool
    _handoff_manage: tuple[list[str], list[str]] | None
    _log_target: str | None
    _log_follower: LogFollower | None
    _log_resume_since: int | None

    def _set_status(self, message: str) -> None: ...

    def _ops_log(self, message: str) -> None: ...

    def _detail_clear(self) -> None: ...

    def _detail_write(self, message: str) -> None: ...

    def _start_refresh(self) -> None: ...

    def _selected_service(self) -> str | None: ...

    def _render_detail(self, name: str) -> None: ...
