"""Compose CLI lifecycle helpers reused by the TUI (non-blocking runners)."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from config import SERVICES
from service_manager import (
    get_compose_cmd,
    sort_for_shutdown,
    sort_for_startup,
)
from utils import iter_env_assignments

ProgressCb = Callable[[str], None]

STDERR_TAIL_LINES = 8
MASK = "***"
_SECRET_KEY = re.compile(r"PASS|SECRET|TOKEN|KEY|CREDENTIAL|PRIVATE|AUTH|SALT|DSN|COOKIE", re.I)
# Values of non-secret-looking keys are still masked once they are long enough to be tokens
# or connection strings; shorter ones (hosts, ports, flags) stay readable in error messages.
_LONG_VALUE = 12
_MIN_SECRET_VALUE = 3


@dataclass(slots=True)
class OpResult:
    ok: bool
    message: str
    failed: list[str]


def plan_manage_changes(
    selected: Sequence[str], running: Sequence[str]
) -> tuple[list[str], list[str]]:
    selected_set = set(selected)
    running_set = set(running)
    to_up = sort_for_startup(selected_set - running_set)
    to_down = sort_for_shutdown(running_set - selected_set)
    return to_up, to_down


def _ensure_network() -> bool:
    """Reuse the CLI network setup in a child process without redirecting TUI stdout."""
    result = subprocess.run(
        [sys.executable, "-c", "from service_manager import ensure_network; ensure_network()"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _env_values_to_mask(service: str) -> list[str]:
    """Known values from the root and service .env files that must never reach the TUI."""
    values: set[str] = set()
    for path in (".env", os.path.join(service, ".env")):
        if not os.path.isfile(path):
            continue
        for key, raw in iter_env_assignments(path):
            value = raw.strip().strip("'\"")
            if value.lower() in ("true", "false") or value.isdigit():
                continue
            if _SECRET_KEY.search(key) and len(value) >= _MIN_SECRET_VALUE:
                values.add(value)
            elif len(value) >= _LONG_VALUE:
                values.add(value)
    # Longest first so a value containing another one is masked whole.
    return sorted(values, key=len, reverse=True)


def mask_known_values(text: str, values: Sequence[str]) -> str:
    for value in values:
        text = text.replace(value, MASK)
    return text


def _stderr_tail(service: str, stderr: str) -> list[str]:
    lines = [line.rstrip() for line in stderr.splitlines() if line.strip()]
    masked = mask_known_values("\n".join(lines[-STDERR_TAIL_LINES:]), _env_values_to_mask(service))
    return masked.splitlines()


def _run_compose(
    service: str,
    args: list[str],
    on_progress: ProgressCb | None = None,
) -> int:
    cmd = get_compose_cmd(service) + args
    if on_progress:
        on_progress(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if on_progress and result.returncode:
        on_progress(f"Compose exited with code {result.returncode}:")
        for line in _stderr_tail(service, result.stderr or ""):
            on_progress(f"  {line}")
        on_progress(f"Full output: make {args[0]} service={service}")
    return result.returncode


def run_action(
    service: str,
    action: str,
    on_progress: ProgressCb | None = None,
) -> OpResult:
    if service not in SERVICES:
        return OpResult(False, f"Unknown service: {service}", [service])
    if action not in ("up", "down", "stop", "restart"):
        return OpResult(False, f"Unsupported action: {action}", [service])

    if action == "up":
        if on_progress:
            on_progress(f"Ensuring shared networks, then starting {service}…")
        if not _ensure_network():
            return OpResult(False, f"Failed to prepare networks for {service}", [service])
        code = _run_compose(service, ["up", "-d"], on_progress)
        if code == 0:
            return OpResult(True, f"{service} started", [])
        return OpResult(False, f"Failed to start {service}", [service])

    if action == "down":
        if on_progress:
            on_progress(f"Stopping and removing {service}…")
        code = _run_compose(service, ["down"], on_progress)
        if code == 0:
            return OpResult(True, f"{service} down", [])
        return OpResult(False, f"Failed to bring down {service}", [service])

    if action == "stop":
        if on_progress:
            on_progress(f"Stopping {service}…")
        code = _run_compose(service, ["stop"], on_progress)
        if code == 0:
            return OpResult(True, f"{service} stopped", [])
        return OpResult(False, f"Failed to stop {service}", [service])

    if on_progress:
        on_progress(f"Restarting {service}…")
    code = _run_compose(service, ["restart"], on_progress)
    if code == 0:
        return OpResult(True, f"{service} restarted", [])
    return OpResult(False, f"Failed to restart {service}", [service])


def apply_manage(
    to_up: Sequence[str],
    to_down: Sequence[str],
    on_progress: ProgressCb | None = None,
) -> OpResult:
    if not to_up and not to_down:
        return OpResult(True, "No changes needed", [])

    failed: list[str] = []
    for service in to_down:
        result = run_action(service, "down", on_progress)
        if not result.ok:
            failed.append(service)
    for service in to_up:
        result = run_action(service, "up", on_progress)
        if not result.ok:
            failed.append(service)

    if failed:
        return OpResult(False, f"Completed with errors: {', '.join(failed)}", failed)
    return OpResult(True, "All changes applied successfully", [])
