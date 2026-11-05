"""Stack identity: ``SANDBOX_NAME`` prefix and shared network names/subnets from the root ``.env``.

An empty ``SANDBOX_NAME`` keeps every historic name. A named stack gets its own Compose
projects, networks, and subnets so several checkouts can share one Docker host.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from dss.core.utils import read_env_value

ROOT_ENV_FILE = ".env"
NETWORK_BASES = ("traefik_proxy", "backend_net", "data_net")
EXIT_USAGE = 2
MAX_SUBNET_BASE = 253  # base, base+1, and base+2 must stay within 0..255

_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _root_value(key: str) -> str:
    env_path = Path(ROOT_ENV_FILE)
    if not env_path.is_file():
        return ""
    return read_env_value(env_path, key) or ""


def stack_name() -> str:
    """The validated ``SANDBOX_NAME``, or an empty string for the unnamed stack."""
    name = _root_value("SANDBOX_NAME")
    if name and not _NAME_PATTERN.match(name):
        raise ValueError(
            f"SANDBOX_NAME={name!r} is invalid; use lowercase letters, digits, '_' or '-'"
        )
    return name


def subnet_base() -> int:
    """The validated ``SANDBOX_SUBNET_BASE`` (default 0)."""
    raw = _root_value("SANDBOX_SUBNET_BASE") or "0"
    try:
        base = int(raw)
    except ValueError:
        raise ValueError(f"SANDBOX_SUBNET_BASE={raw!r} is invalid; use an integer") from None
    if not 0 <= base <= MAX_SUBNET_BASE:
        raise ValueError(f"SANDBOX_SUBNET_BASE={base} is invalid; use 0 to {MAX_SUBNET_BASE}")
    return base


def project_name(service: str) -> str:
    """Compose project for a service: ``<SANDBOX_NAME>-<service>`` or the bare service name."""
    name = stack_name()
    return f"{name}-{service}" if name else service


def network_name(base: str) -> str:
    """Docker network name for a base such as ``data_net``."""
    name = stack_name()
    return f"{name}_{base}" if name else base


def network_pairs() -> list[str]:
    """``name:subnet`` for each shared network, adjacent /16s in 10/8 from the base."""
    first = subnet_base()
    return [
        f"{network_name(base)}:10.{first + offset}.0.0/16"
        for offset, base in enumerate(NETWORK_BASES)
    ]


def main(argv: list[str]) -> int:
    try:
        if argv[1:] == ["name"]:
            print(stack_name())
        elif len(argv) == 1:
            print("\n".join(network_pairs()))
        else:
            print("usage: python -m dss.core.stack [name]", file=sys.stderr)
            return EXIT_USAGE
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
