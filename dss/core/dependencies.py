"""Backend ordering derived from ``PACKAGE_REQUIRES`` and ``START_ORDER``."""

from collections.abc import Iterable

from dss.core.config import PACKAGE_REQUIRES, START_ORDER


def direct_dependencies(service: str, available: set[str] | None = None) -> list[str]:
    """Backends ``service`` must reach before it starts. ``available`` limits the set."""
    backends: list[str] = []
    for backend, consumers in PACKAGE_REQUIRES.items():
        if service not in consumers or backend == service:
            continue
        if available is not None and backend not in available:
            continue
        backends.append(backend)
    order_map = {name: index for index, name in enumerate(START_ORDER)}
    return sorted(set(backends), key=lambda name: (order_map.get(name, 999), name))


def dependency_queue(service: str, available: set[str] | None = None) -> list[str]:
    """Transitive backends that must be ready before ``service``, in startup order."""
    seen: list[str] = []

    def walk(name: str) -> None:
        for dep in direct_dependencies(name, available):
            if dep in seen:
                continue
            walk(dep)
            seen.append(dep)

    walk(service)
    return startup_queue(seen)


def startup_queue(services: Iterable[str]) -> list[str]:
    """Dependency order, using ``START_ORDER`` when several services are ready together."""
    selected = list(dict.fromkeys(services))
    selected_set = set(selected)
    deps = {
        name: [dep for dep in direct_dependencies(name) if dep in selected_set] for name in selected
    }
    order_map = {name: index for index, name in enumerate(START_ORDER)}
    remaining = set(selected)
    queued: list[str] = []
    while remaining:
        ready = [name for name in remaining if all(dep not in remaining for dep in deps[name])]
        if not ready:
            queued.extend(sorted(remaining, key=lambda name: (order_map.get(name, 999), name)))
            break
        ready.sort(key=lambda name: (order_map.get(name, 999), name))
        chosen = ready[0]
        queued.append(chosen)
        remaining.remove(chosen)
    return queued
