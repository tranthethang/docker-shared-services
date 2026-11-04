"""Shared data models for the Textual service manager."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ContainerInfo:
    name: str
    status: str
    health: str
    image: str
    compose_service: str
    # A one-shot init container that exited 0. It does not count toward the stack state.
    completed: bool = False


@dataclass(slots=True)
class ServiceStatus:
    name: str
    state: str
    health: str
    container_count: int
    running_count: int
    containers: list[ContainerInfo] = field(default_factory=list)
    error: str = ""
