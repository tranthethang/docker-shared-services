"""Lifecycle / manage / log actions for ServiceManagerApp."""

from __future__ import annotations

from functools import partial

from tui.compose_ops import OpResult, apply_manage, plan_manage_changes, run_action
from tui.docker_state import (
    DockerStateError,
    LogFollower,
    connect_client,
    list_service_statuses,
)
from tui.screens import ConfirmScreen

LOG_TAIL = 200


class OpsMixin:
    """Mixin expecting ServiceManagerApp attributes and helpers."""

    def action_load_logs(self) -> None:
        name = self._selected_service()
        if not name:
            return
        if self._log_target == name:
            self._stop_logs()
            self._set_status(f"Stopped following logs for {name}")
            self._render_detail(name)
            return
        self._start_logs(name)

    def _start_logs(self, name: str, since: int | None = None) -> None:
        self._stop_logs()
        row = next((r for r in self._rows if r.name == name), None)
        detail = self.query_one("#detail")
        if row is None or not row.containers:
            self._detail_clear()
            self._detail_write(f"No containers for {name}")
            return
        self._log_target = name
        if since is None:
            self._detail_clear()
        detail.border_title = f"Logs · {name} (following, l to stop)"
        self._set_status(f"Following logs for {name}… (press l to stop)")
        # Reattaching after a restart/recreate only fetches lines produced since the old
        # stream ended, so nothing is shown twice.
        follower = LogFollower(row.containers, tail="all" if since else LOG_TAIL, since=since)
        self._log_follower = follower
        self.run_worker(partial(self._start_follower_worker, follower, name), thread=True)

    def _start_follower_worker(self, follower: LogFollower, name: str) -> None:
        try:
            follower.start()
        except DockerStateError as exc:
            self.call_from_thread(self._apply_log_error, follower, name, str(exc))

    def _stop_logs(self) -> None:
        if self._log_follower is not None:
            self._log_follower.stop()
            self._log_follower = None
        self._log_target = None
        self._log_resume_since = None

    def _drain_logs(self) -> None:
        follower = self._log_follower
        if follower is None:
            return
        while follower.errors:
            self._ops_log(follower.errors.popleft())
        if follower.lines:
            batch = [follower.lines.popleft() for _ in range(len(follower.lines))]
            self._detail_write("\n".join(batch))
        if follower.done and not follower.lines:
            name = self._log_target
            self._log_follower = None
            self.query_one("#detail").border_title = f"Logs · {name} (stream ended, waiting…)"
            self._detail_write("── log stream ended (container stopped or recreated) ──")
            self._log_resume_since = follower.ended_at

    def _resume_logs_after_refresh(self) -> None:
        """Reattach a log view whose containers came back (e.g. after restart)."""
        name = self._log_target
        since = self._log_resume_since
        if not name or since is None or self._log_follower is not None:
            return
        row = next((r for r in self._rows if r.name == name), None)
        if row is not None and row.running_count > 0:
            self._log_resume_since = None
            self._start_logs(name, since=since)

    def _apply_log_error(self, follower: LogFollower, name: str, message: str) -> None:
        if self._log_follower is follower:
            self._stop_logs()
        self._set_status(message)
        self._ops_log(message)

    def action_op_up(self) -> None:
        self._start_single_op("up")

    def action_op_stop(self) -> None:
        self._start_single_op("stop")

    def action_op_restart(self) -> None:
        self._start_single_op("restart")

    def action_op_down(self) -> None:
        name = self._selected_service()
        if not name or self._busy:
            return
        body = f"Bring down stack '{name}'?\nContainers will be stopped and removed."
        self.push_screen(
            ConfirmScreen("Confirm down", body),
            lambda ok: self._confirm_down(ok, name),
        )

    def _confirm_down(self, confirmed: bool | None, name: str) -> None:
        if not confirmed:
            self._set_status("Down cancelled")
            return
        self._run_op_async(name, "down")

    def _start_single_op(self, action: str) -> None:
        name = self._selected_service()
        if not name or self._busy:
            return
        self._run_op_async(name, action)

    def action_apply_manage(self) -> None:
        if self._busy:
            return
        selected = sorted(self._manage) if self._manage else []
        self._busy = True
        self._set_status("Checking current services for manage changes…")
        self.run_worker(partial(self._manage_plan_worker, selected), exclusive=False, thread=True)

    def _manage_plan_worker(self, selected: list[str]) -> None:
        client = None
        try:
            client = connect_client()
            rows = list_service_statuses(client)
            running = [row.name for row in rows if row.running_count > 0]
            to_up, to_down = plan_manage_changes(selected, running)
            self.call_from_thread(self._show_manage_confirmation, to_up, to_down)
        except Exception as exc:
            self.call_from_thread(self._finish_manage_plan_error, str(exc))
        finally:
            if client is not None:
                client.close()

    def _finish_manage_plan_error(self, message: str) -> None:
        self._busy = False
        self._set_status(f"Could not plan manage changes: {message}")

    def _show_manage_confirmation(self, to_up: list[str], to_down: list[str]) -> None:
        if not to_up and not to_down:
            self._busy = False
            self._set_status("No changes needed for current selection")
            return
        lines = []
        if to_up:
            lines.append("Will start: " + ", ".join(to_up))
        if to_down:
            lines.append("Will stop:  " + ", ".join(to_down))
        self.push_screen(
            ConfirmScreen("Confirm manage changes", "\n".join(lines)),
            lambda ok: self._confirm_manage(ok, to_up, to_down),
        )

    def _confirm_manage(self, confirmed: bool | None, to_up: list[str], to_down: list[str]) -> None:
        if not confirmed:
            self._busy = False
            self._set_status("Manage cancelled")
            return
        self._run_manage_async(to_up, to_down)

    def _run_op_async(self, service: str, action: str) -> None:
        self._busy = True
        self._set_status(f"Running {action} on {service}…")
        self._ops_log(f"→ {action} {service}")
        self.run_worker(
            partial(self._op_worker, service, action), exclusive=True, thread=True, group="compose"
        )

    def _op_worker(self, service: str, action: str) -> None:
        def progress(msg: str) -> None:
            self.call_from_thread(self._ops_log, msg)

        try:
            result = run_action(service, action, on_progress=progress)
        except Exception as exc:
            result = OpResult(False, f"{action} failed ({type(exc).__name__})", [service])
        self.call_from_thread(self._finish_op, result, False)

    def _run_manage_async(self, to_up: list[str], to_down: list[str]) -> None:
        self._busy = True
        self._set_status("Applying manage changes…")
        self.run_worker(
            partial(self._manage_worker, to_up, to_down),
            exclusive=True,
            thread=True,
            group="compose",
        )

    def _manage_worker(self, to_up: list[str], to_down: list[str]) -> None:
        def progress(msg: str) -> None:
            self.call_from_thread(self._ops_log, msg)

        try:
            result = apply_manage(to_up, to_down, on_progress=progress)
        except Exception as exc:
            result = OpResult(False, f"Manage failed ({type(exc).__name__})", [])
        self.call_from_thread(self._finish_op, result, True)

    def _finish_op(self, result: OpResult, was_manage: bool) -> None:
        self._busy = False
        if was_manage:
            self._manage_dirty = False
        self._ops_log(("OK: " if result.ok else "ERR: ") + result.message)
        self._set_status(result.message)
        self._start_refresh()
