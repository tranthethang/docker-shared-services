"""A container is ready when it runs healthy, or when it is a one-shot that exited 0."""

from __future__ import annotations

import pytest

from dss.cli.readiness import parse_inspect_ready
from dss.core.container_state import is_completed_oneshot, is_container_ready


@pytest.mark.parametrize(
    ("status", "health", "exit_code", "policy", "ready"),
    [
        ("running", "none", 0, "unless-stopped", True),
        ("running", "healthy", 0, "unless-stopped", True),
        ("running", "starting", 0, "unless-stopped", False),
        ("running", "unhealthy", 0, "unless-stopped", False),
        ("exited", "none", 0, "no", True),
        ("exited", "none", 0, "", True),
        ("exited", "none", 1, "no", False),
        ("exited", "none", 0, "unless-stopped", False),
        ("created", "none", 0, "no", False),
        ("restarting", "none", 0, "always", False),
    ],
)
def test_is_container_ready(
    status: str, health: str, exit_code: int, policy: str, ready: bool
) -> None:
    assert is_container_ready(status, health, exit_code, policy) is ready


def test_is_completed_oneshot_ignores_running_container() -> None:
    assert not is_completed_oneshot("running", 0, "no")


@pytest.mark.parametrize(
    ("output", "ready"),
    [
        ("running healthy 0 unless-stopped\n", True),
        ("exited none 0 no\n", True),
        ("exited none 137 no\n", False),
        ("exited none 0 unless-stopped\n", False),
        ("running healthy\n", False),
        ("running none x no\n", False),
        ("", False),
    ],
)
def test_parse_inspect_ready(output: str, ready: bool) -> None:
    assert parse_inspect_ready(output) is ready
