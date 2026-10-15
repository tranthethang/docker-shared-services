"""Start a service's backends and wait until each is running and healthy."""

import subprocess
import time
from collections.abc import Callable

from dss.cli.compose import get_compose_cmd
from dss.core.dependencies import dependency_queue
from dss.core.utils import error, success

# A database can spend its start_period plus several probe retries before it accepts clients.
READY_TIMEOUT_SECONDS = 300
# `docker inspect` prints "<status> <health>".
_INSPECT_FIELDS = 2

Announce = Callable[[str], None]


def _say(message: str, announce: Announce | None) -> None:
    if announce:
        announce(message)
    else:
        print(message)


def _container_ids(service: str) -> list[str]:
    result = subprocess.run(
        [*get_compose_cmd(service), "ps", "-aq"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _container_ready(container_id: str) -> bool:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            container_id,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    parts = result.stdout.split()
    if len(parts) < _INSPECT_FIELDS:
        return False
    status, health = parts[0], parts[1]
    return status == "running" and health in ("none", "healthy")


def wait_until_ready(
    service: str, timeout: int = READY_TIMEOUT_SECONDS, announce: Announce | None = None
) -> bool:
    """Block until every container in ``service`` is running and healthy when probed."""
    ids = _container_ids(service)
    if not ids:
        error(f"{service} has no containers")
        return False
    if all(_container_ready(container_id) for container_id in ids):
        return True

    _say(f"ℹ️  Waiting until {service} is ready...", announce)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        time.sleep(2)
        ids = _container_ids(service)
        if ids and all(_container_ready(container_id) for container_id in ids):
            success(f"{service} is ready")
            return True
    error(f"{service} was not ready within {timeout}s")
    return False


def _service_is_ready(service: str) -> bool:
    ids = _container_ids(service)
    return bool(ids) and all(_container_ready(container_id) for container_id in ids)


def ensure_dependencies_ready(service: str, announce: Announce | None = None) -> bool:
    """Start missing backends, then wait until each one is ready."""
    from dss.core.env_report import check_prerequisites

    for dependency in dependency_queue(service):
        if _service_is_ready(dependency):
            continue
        _say(f"ℹ️  Queuing {dependency} before {service}...", announce)
        if not check_prerequisites(dependency):
            error(f"Cannot start {service}: prerequisite checks failed for {dependency}")
            return False
        result = subprocess.run([*get_compose_cmd(dependency), "up", "-d"])
        if result.returncode != 0:
            error(f"Failed to start dependency {dependency}")
            return False
        if not wait_until_ready(dependency, announce=announce):
            error(f"Cannot start {service}: dependency {dependency} is not ready")
            return False
    return True
