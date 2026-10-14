"""Pin today's dependency ordering so later refactors cannot change it silently."""

from __future__ import annotations

from config import (
    PACKAGE_REQUIRES,
    dependency_queue,
    direct_dependencies,
    startup_queue,
)


def test_direct_dependencies_follow_package_requires() -> None:
    assert direct_dependencies("zitadel") == ["postgres"]
    assert direct_dependencies("oauth2-proxy") == ["zitadel"]
    assert direct_dependencies("inngest") == ["postgres", "redis"]
    assert direct_dependencies("hindsight") == ["pgvector"]
    assert direct_dependencies("redisinsight") == ["redis"]
    assert direct_dependencies("postgres") == []
    assert direct_dependencies("traefik") == []


def test_direct_dependencies_honor_available_set() -> None:
    assert direct_dependencies("oauth2-proxy", available={"oauth2-proxy"}) == []
    assert direct_dependencies("inngest", available={"inngest", "redis"}) == ["redis"]


def test_dependency_queue_is_transitive_and_ordered() -> None:
    assert dependency_queue("zitadel") == ["postgres"]
    assert dependency_queue("oauth2-proxy") == ["postgres", "zitadel"]
    assert dependency_queue("inngest") == ["postgres", "redis"]
    assert dependency_queue("postgres") == []
    assert dependency_queue("oauth2-proxy", available={"zitadel", "oauth2-proxy"}) == ["zitadel"]


def test_startup_queue_starts_backends_first() -> None:
    assert startup_queue(["oauth2-proxy", "zitadel", "postgres", "redis", "inngest"]) == [
        "postgres",
        "zitadel",
        "oauth2-proxy",
        "redis",
        "inngest",
    ]
    assert startup_queue(["oauth2-proxy", "zitadel"]) == ["zitadel", "oauth2-proxy"]
    assert startup_queue([]) == []


def test_package_requires_has_no_cycles() -> None:
    graph: dict[str, set[str]] = {}
    for backend, consumers in PACKAGE_REQUIRES.items():
        for consumer in consumers:
            graph.setdefault(consumer, set()).add(backend)
            graph.setdefault(backend, set())

    visiting: set[str] = set()
    visited: set[str] = set()

    def walk(name: str) -> None:
        if name in visiting:
            raise AssertionError(f"cycle through {name}")
        if name in visited:
            return
        visiting.add(name)
        for dep in graph[name]:
            walk(dep)
        visiting.remove(name)
        visited.add(name)

    for name in graph:
        walk(name)
