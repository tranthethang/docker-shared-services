"""`restart: "no"` marks a one-shot init container, so readiness may treat exit 0 as done.

Every other service must set a restart policy. Otherwise a long-running server that
exits 0 would look ready to `make up` and to the TUI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILES = sorted(REPO_ROOT.glob("*/docker-compose.yml"))

_TOP_LEVEL = re.compile(r"^\S")
_SERVICE = re.compile(r"^  ([\w.-]+):\s*$")
_RESTART = re.compile(r"^    restart:\s*(.+?)\s*$")
_COMPLETED_DEP = re.compile(
    r"^      ([\w.-]+):\n        condition: service_completed_successfully\s*$", re.MULTILINE
)


def _service_restarts(compose: Path) -> dict[str, str | None]:
    """Read each service's restart value from the repo's 2-space compose layout."""
    services: dict[str, str | None] = {}
    in_services = False
    current = ""
    for line in compose.read_text(encoding="utf-8").splitlines():
        if _TOP_LEVEL.match(line):
            in_services = line.startswith("services:")
            continue
        if not in_services:
            continue
        if match := _SERVICE.match(line):
            current = match.group(1)
            services[current] = None
        elif current and (match := _RESTART.match(line)):
            services[current] = match.group(1).strip("'\"")
    return services


@pytest.mark.parametrize("compose", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_every_service_declares_restart(compose: Path) -> None:
    missing = [name for name, restart in _service_restarts(compose).items() if not restart]
    assert not missing, f"{compose.parent.name}: set restart on {missing}"


@pytest.mark.parametrize("compose", COMPOSE_FILES, ids=lambda p: p.parent.name)
def test_oneshot_services_are_completion_dependencies(compose: Path) -> None:
    oneshots = {name for name, restart in _service_restarts(compose).items() if restart == "no"}
    awaited = set(_COMPLETED_DEP.findall(compose.read_text(encoding="utf-8")))
    stray = sorted(oneshots - awaited)
    assert not stray, (
        f"{compose.parent.name}: {stray} use restart 'no' but no service waits on them "
        "with condition: service_completed_successfully"
    )


def test_reader_finds_garage_init() -> None:
    restarts = _service_restarts(REPO_ROOT / "garage" / "docker-compose.yml")
    assert restarts["garage-config-init"] == "no"
    assert restarts["garage"] == "${RESTART_POLICY:-unless-stopped}"
