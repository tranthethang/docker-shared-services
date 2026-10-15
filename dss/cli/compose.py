"""Compose commands, shared networks, validation, and start/stop ordering per service."""

import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

from dss.core.config import SERVICES, START_ORDER
from dss.core.dependencies import startup_queue
from dss.core.service_catalog import catalog_problems, load_catalog
from dss.core.utils import error, success, warning

# Bridges cannot share one CIDR; adjacent /16s in 10/8.
SHARED_NETWORKS = (
    ("traefik_proxy", "10.0.0.0/16"),
    ("backend_net", "10.1.0.0/16"),
    ("data_net", "10.2.0.0/16"),
)


def _docker_network_exists(name: str) -> bool:
    return (
        subprocess.run(
            ["docker", "network", "inspect", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def ensure_network() -> None:
    for name, subnet in SHARED_NETWORKS:
        if _docker_network_exists(name):
            continue

        print(f"ℹ️  Creating network {name}...")
        attempted = subprocess.run(
            [
                "docker",
                "network",
                "create",
                name,
                "--subnet",
                subnet,
                "--driver",
                "bridge",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

        if attempted.returncode == 0:
            success(f"Network {name} created ({subnet})")
            continue

        err = (attempted.stderr or "").lower()
        if "overlap" in err or "pool" in err:
            warning(
                f"Subnet {subnet} for {name} overlaps another Docker address pool; "
                "creating the bridge with an auto-assigned subnet instead."
            )
            warning(
                "Stacks still reach containers by name on this network. To pin 10.0.x.x/10.1.x.x, "
                "adjust Docker default-address-pools or remove the conflicting network."
            )
            subprocess.run(
                ["docker", "network", "create", name, "--driver", "bridge"],
                check=True,
            )
            success(f"Network {name} created (auto subnet)")
            continue

        sys.stderr.write(attempted.stderr or "")
        raise subprocess.CalledProcessError(
            attempted.returncode,
            attempted.args,
            attempted.stderr,
        )


def get_compose_cmd(service: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-directory",
        service,
        "-f",
        "docker-compose.shared.yml",
        "-f",
        f"{service}/docker-compose.yml",
    ]


def _check_compose_config(service: str) -> tuple[bool, bool]:
    """Run ``compose config``; report problems. Returns (parsed, clean)."""
    result = subprocess.run(
        [*get_compose_cmd(service), "config"],
        capture_output=True,
        text=True,
    )
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        error(f"{service}: invalid")
        if stderr:
            print(stderr, file=sys.stderr)
        return False, False
    if stderr:
        # Unset-variable warnings still mean config is usable but incomplete.
        warning(f"{service}: {stderr.splitlines()[0]}")
        if stderr.count("\n") > 0:
            print(stderr, file=sys.stderr)
        return True, False
    return True, True


def _listed_services(service: str) -> list[str] | None:
    listed = subprocess.run(
        [*get_compose_cmd(service), "config", "--services"],
        capture_output=True,
        text=True,
    )
    if listed.returncode != 0:
        return None
    return [line.strip() for line in listed.stdout.splitlines() if line.strip()]


def validate_all_compose() -> None:
    """Validate each service with --project-directory so service/.env is loaded."""
    print("Validating Docker Compose configuration...")
    failed: list[str] = []
    compose_services: dict[str, list[str]] = {}

    for service in sorted(SERVICES):
        compose_file = Path(service) / "docker-compose.yml"
        if not compose_file.is_file():
            error(f"{service}: missing {compose_file}")
            failed.append(service)
            continue
        parsed, clean = _check_compose_config(service)
        if not clean:
            failed.append(service)
        names = _listed_services(service) if parsed else None
        if names is not None:
            compose_services[service] = names

    print("Validating service catalog (dss/core/service_catalog.json)...")
    problems = catalog_problems(load_catalog(), compose_services)
    for problem in problems:
        error(problem)
    if problems:
        failed.append("service_catalog.json")

    if failed:
        error(f"Validation failed for: {', '.join(failed)}")
        sys.exit(1)

    success("Compose configuration and service catalog are valid")


def get_stack_services(service: str) -> list[str]:
    """Compose service names in a stack directory (e.g. otel -> grafana, loki, alloy)."""
    result = subprocess.run(
        [*get_compose_cmd(service), "config", "--services"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [service]
    names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return names or [service]


def is_service_running(service: str) -> bool:
    stack_services = get_stack_services(service)
    result = subprocess.run(
        [*get_compose_cmd(service), "ps", "-q", "--status", "running", *stack_services],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def get_running_services() -> list[str]:
    return [s for s in SERVICES if is_service_running(s)]


def sort_for_startup(services: Iterable[str]) -> list[str]:
    return startup_queue(services)


def sort_for_shutdown(services: Iterable[str]) -> list[str]:
    order_map = {s: i for i, s in enumerate(START_ORDER)}

    def shutdown_key(service: str) -> tuple[int, str]:
        if service == "traefik":
            return (-1, service)
        return (order_map.get(service, 500), service)

    return sorted(services, key=shutdown_key, reverse=True)
