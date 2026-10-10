"""Read container status/health/logs via the Docker Engine API."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

from config import SERVICES
from tui.models import ContainerInfo, ServiceStatus

COMPOSE_PROJECT_LABEL = "com.docker.compose.project"
COMPOSE_SERVICE_LABEL = "com.docker.compose.service"


class DockerStateError(Exception):
    """Raised when the Docker Engine is unreachable or returns an error."""


def connect_client() -> Any:
    try:
        import docker
    except ImportError as exc:
        raise DockerStateError(
            "Python package 'docker' is missing. Run: uv sync --group tui"
        ) from exc

    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as exc:  # docker SDK raises several connection types
        raise DockerStateError(
            f"Cannot connect to Docker Engine: {exc}. "
            "Is Docker running? Non-TUI: make ps / make manage"
        ) from exc


def _health_from_attrs(attrs: dict[str, Any]) -> str:
    state = attrs.get("State") or {}
    if not isinstance(state, dict):
        return "-"
    health = state.get("Health") or {}
    status = health.get("Status")
    if status:
        return str(status)
    if state.get("Running"):
        return "none"
    return "-"


def _state_label(running: int, total: int) -> str:
    if total == 0:
        return "absent"
    if running == 0:
        return "stopped"
    if running < total:
        return "partial"
    return "running"


def _aggregate_health(containers: list[ContainerInfo]) -> str:
    if not containers:
        return "-"
    values = {c.health for c in containers}
    if "unhealthy" in values:
        return "unhealthy"
    if "starting" in values:
        return "starting"
    if "healthy" in values:
        return "healthy"
    if "none" in values:
        return "none"
    return "-"


def list_service_statuses(client: Any) -> list[ServiceStatus]:
    """Map Engine containers to configured Compose stacks (one row per service)."""
    by_project: dict[str, list[ContainerInfo]] = {name: [] for name in SERVICES}

    try:
        containers = client.containers.list(all=True)
    except Exception as exc:
        raise DockerStateError(f"Failed to list containers: {exc}") from exc

    for container in containers:
        labels = container.labels or {}
        project = labels.get(COMPOSE_PROJECT_LABEL)
        if project not in by_project:
            continue
        try:
            container.reload()
        except Exception:
            # A container can disappear between list and inspect during a Compose action.
            continue
        attrs = container.attrs or {}
        compose_svc = labels.get(COMPOSE_SERVICE_LABEL) or container.name
        by_project[project].append(
            ContainerInfo(
                name=container.name,
                status=container.status or "unknown",
                health=_health_from_attrs(attrs),
                image=str((attrs.get("Config") or {}).get("Image") or ""),
                compose_service=str(compose_svc),
            )
        )

    rows: list[ServiceStatus] = []
    for name in SERVICES:
        containers = by_project[name]
        running = sum(1 for c in containers if c.status == "running")
        rows.append(
            ServiceStatus(
                name=name,
                state=_state_label(running, len(containers)),
                health=_aggregate_health(containers),
                container_count=len(containers),
                running_count=running,
                containers=containers,
            )
        )
    return rows


class LogFollower:
    """Stream `docker logs -f` for every container of one stack on daemon threads.

    Lines are queued rather than pushed to the UI, so a burst never floods the event loop;
    the app drains `lines` on a timer. `stop()` closes the HTTP streams, which unblocks the
    reader threads immediately.
    """

    def __init__(
        self,
        containers: list[ContainerInfo],
        tail: int | str = 200,
        since: int | None = None,
    ) -> None:
        self.lines: deque[str] = deque()
        self.errors: deque[str] = deque()
        self.ended_at: int | None = None
        self._containers = containers
        self._tail = tail
        self._since = since
        self._prefix = len(containers) > 1
        self._client: Any = None
        self._streams: list[Any] = []
        self._lock = threading.Lock()
        self._live = 0
        self._stopped = False

    @property
    def done(self) -> bool:
        return self.ended_at is not None

    def start(self) -> None:
        self._client = connect_client()
        self._live = len(self._containers)
        for info in self._containers:
            threading.Thread(target=self._follow, args=(info,), daemon=True).start()

    def stop(self) -> None:
        with self._lock:
            self._stopped = True
            streams = list(self._streams)
        for stream in streams:
            try:
                stream.close()
            except Exception:
                pass
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass

    def _follow(self, info: ContainerInfo) -> None:
        prefix = f"[{info.compose_service}] " if self._prefix else ""
        pending = ""
        try:
            container = self._client.containers.get(info.name)
            stream = container.logs(
                stream=True, follow=True, tail=self._tail, since=self._since, timestamps=False
            )
            with self._lock:
                if self._stopped:
                    stream.close()
                    return
                self._streams.append(stream)
            for chunk in stream:
                text = pending + chunk.decode("utf-8", errors="replace")
                *complete, pending = text.split("\n")
                self.lines.extend(prefix + line for line in complete)
            if pending:
                self.lines.append(prefix + pending)
        except Exception as exc:
            if not self._stopped:
                self.errors.append(f"Log stream for {info.name} failed: {exc}")
        finally:
            with self._lock:
                self._live -= 1
                if self._live == 0 and not self._stopped:
                    self.ended_at = int(time.time())


# Container lifecycle/health actions that change what the dashboard shows. Exec events from
# healthchecks fire constantly and are ignored.
_STATE_EVENTS = (
    "create",
    "start",
    "restart",
    "stop",
    "die",
    "kill",
    "destroy",
    "pause",
    "unpause",
    "health_status",
)


class EventWatcher:
    """Call `on_change` whenever a Compose-managed container changes state.

    Runs on a daemon thread and reconnects with a delay if the Docker Engine goes away.
    """

    RECONNECT_DELAY = 5.0

    def __init__(self, on_change: Callable[[], None]) -> None:
        self._on_change = on_change
        self._stopped = threading.Event()
        self._lock = threading.Lock()
        self._client: Any = None
        self._stream: Any = None

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self) -> None:
        self._stopped.set()
        with self._lock:
            stream, client = self._stream, self._client
        for closable in (stream, client):
            if closable is None:
                continue
            try:
                closable.close()
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                client = connect_client()
                stream = client.events(
                    decode=True,
                    filters={"type": "container", "label": COMPOSE_PROJECT_LABEL},
                )
                with self._lock:
                    self._client, self._stream = client, stream
                if self._stopped.is_set():
                    break
                for event in stream:
                    action = str(event.get("Action") or event.get("status") or "")
                    if action.split(":", 1)[0] in _STATE_EVENTS:
                        self._on_change()
            except Exception:
                pass
            finally:
                with self._lock:
                    client, self._client, self._stream = self._client, None, None
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        pass
            self._stopped.wait(self.RECONNECT_DELAY)
