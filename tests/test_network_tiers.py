"""Network tiers: data stores sit on data_net only, and only declared clients join it."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from dss.core.config import DATA_CLIENT_UI_SERVICES, PACKAGE_REQUIRES
from dss.core.service_catalog import load_catalog

REPO_ROOT = Path(__file__).resolve().parents[1]

# Compose service names that hold data, keyed by service directory.
DATA_STORES: dict[str, set[str]] = {
    "chromadb": {"chromadb"},
    "kafka": {"kafka"},
    "mariadb": {"mariadb"},
    "memcached": {"memcached"},
    "mongodb": {"mongodb"},
    "mysql8": {"mysql8"},
    "otel": {"loki"},
    "pgvector": {"pgvector"},
    "postgres": {"postgres"},
    "qdrant": {"qdrant"},
    "rabbitmq": {"rabbitmq"},
    "redis": {"redis"},
    "supabase": {"supabase-db"},
}

_TOP_LEVEL = re.compile(r"^\S")
_SERVICE = re.compile(r"^  ([\w.-]+):\s*$")
_NETWORK_ITEM = re.compile(r"^      (?:- )?([\w.-]+):?\s*$")


def _service_networks(compose: Path) -> dict[str, list[str]]:
    """Read services and their networks from the repo's 2-space compose layout.

    The dev tooling has no YAML parser; every compose file here uses the same
    layout, and the catalog check below catches a service this reader misses.
    """
    services: dict[str, list[str]] = {}
    in_services = in_networks = False
    current = ""
    for line in compose.read_text(encoding="utf-8").splitlines():
        if _TOP_LEVEL.match(line):
            in_services = line.startswith("services:")
            continue
        if not in_services:
            continue
        if match := _SERVICE.match(line):
            current = match.group(1)
            services[current] = []
            in_networks = False
        elif line.startswith("    ") and not line.startswith("     "):
            in_networks = line.strip() == "networks:"
        elif in_networks and (match := _NETWORK_ITEM.match(line)):
            services[current].append(match.group(1))
    return services


@pytest.fixture(scope="module")
def networks() -> dict[str, dict[str, list[str]]]:
    return {
        path.parent.name: _service_networks(path)
        for path in sorted(REPO_ROOT.glob("*/docker-compose.yml"))
    }


def test_reader_sees_every_catalog_container(networks: dict[str, dict[str, list[str]]]) -> None:
    catalog = load_catalog()
    for name, services in networks.items():
        assert set(services) == set(catalog[name]["containers"]), name


def test_data_stores_use_data_net_not_backend_net(
    networks: dict[str, dict[str, list[str]]],
) -> None:
    for project, stores in DATA_STORES.items():
        for store in stores:
            nets = networks[project][store]
            assert "data_net" in nets, f"{project}/{store}"
            assert "backend_net" not in nets, f"{project}/{store}"


def test_only_declared_clients_join_data_net(networks: dict[str, dict[str, list[str]]]) -> None:
    consumers = {name for backend in DATA_STORES for name in PACKAGE_REQUIRES.get(backend, [])}
    allowed = consumers | set(DATA_CLIENT_UI_SERVICES) | set(DATA_STORES)
    for project, services in networks.items():
        for service, nets in services.items():
            if "data_net" in nets and service not in DATA_STORES.get(project, set()):
                assert project in allowed, f"{project}/{service} joins data_net undeclared"


def test_package_consumers_can_reach_data_net(networks: dict[str, dict[str, list[str]]]) -> None:
    for backend in DATA_STORES:
        for consumer in PACKAGE_REQUIRES.get(backend, []):
            services = networks[consumer].values()
            assert any("data_net" in nets for nets in services), f"{consumer} needs {backend}"
