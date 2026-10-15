"""Compose CLI lifecycle helpers reused by the TUI (non-blocking runners)."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from dss.cli.compose import get_compose_cmd, sort_for_shutdown, sort_for_startup
from dss.cli.readiness import ensure_dependencies_ready
from dss.core.config import SERVICES
from dss.core.start_gate import label_only_reason
from dss.core.utils import iter_env_assignments

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
    frozen = {name for name in (*selected, *running) if label_only_reason(name)}
    selected_set = set(selected) - frozen
    running_set = set(running) - frozen
    to_up = sort_for_startup(selected_set - running_set)
    to_down = sort_for_shutdown(running_set - selected_set)
    return to_up, to_down


def _ensure_network() -> bool:
    """Reuse the CLI network setup in a child process without redirecting TUI stdout."""
    result = subprocess.run(
        [sys.executable, "-c", "from dss.cli.compose import ensure_network; ensure_network()"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _should_mask(key: str, value: str) -> bool:
    if value.lower() in ("true", "false") or value.isdigit():
        return False
    if _SECRET_KEY.search(key):
        return len(value) >= _MIN_SECRET_VALUE
    return len(value) >= _LONG_VALUE


def _env_values_to_mask(service: str) -> list[str]:
    """Known values from the root and service .env files that must never reach the TUI."""
    values: set[str] = set()
    for path in (Path(".env"), Path(service) / ".env"):
        if not path.is_file():
            continue
        for key, raw in iter_env_assignments(path):
            value = raw.strip().strip("'\"")
            if _should_mask(key, value):
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
    cmd = [*get_compose_cmd(service), *args]
    if on_progress:
        on_progress(f"$ {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if on_progress and result.returncode:
        on_progress(f"Compose exited with code {result.returncode}:")
        for line in _stderr_tail(service, result.stderr or ""):
            on_progress(f"  {line}")
        on_progress(f"Full output: make {args[0]} service={service}")
    return result.returncode


# action -> (progress message, compose args, done message, failure message)
_ACTIONS = {
    "up": ("", ["up", "-d"], "{service} started", "Failed to start {service}"),
    "down": (
        "Stopping and removing {service}…",
        ["down"],
        "{service} down",
        "Failed to bring down {service}",
    ),
    "stop": ("Stopping {service}…", ["stop"], "{service} stopped", "Failed to stop {service}"),
    "restart": (
        "Restarting {service}…",
        ["restart"],
        "{service} restarted",
        "Failed to restart {service}",
    ),
}


def _prepare_up(service: str, on_progress: ProgressCb | None) -> OpResult | None:
    """Networks and backends for ``up``; returns a failure result, or None when ready."""
    if on_progress:
        on_progress(f"Ensuring shared networks, then starting {service}…")
    if not _ensure_network():
        return OpResult(False, f"Failed to prepare networks for {service}", [service])
    if not ensure_dependencies_ready(service, announce=on_progress):
        return OpResult(False, f"Failed to start {service}: a dependency is not ready", [service])
    return None


def run_action(
    service: str,
    action: str,
    on_progress: ProgressCb | None = None,
) -> OpResult:
    if service not in SERVICES:
        return OpResult(False, f"Unknown service: {service}", [service])
    if action not in _ACTIONS:
        return OpResult(False, f"Unsupported action: {action}", [service])
    if action in ("up", "restart"):
        reason = label_only_reason(service)
        if reason:
            return OpResult(False, f"Cannot {action} {service}: {reason}", [service])

    progress, args, done, failure = _ACTIONS[action]
    if action == "up":
        blocked = _prepare_up(service, on_progress)
        if blocked is not None:
            return blocked
    elif on_progress:
        on_progress(progress.format(service=service))
    if _run_compose(service, args, on_progress) == 0:
        return OpResult(True, done.format(service=service), [])
    return OpResult(False, failure.format(service=service), [service])
