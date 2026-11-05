"""Remove every service stack and its volumes (``make remove-all``)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dss.cli.compose import get_compose_cmd, sort_for_shutdown
from dss.core.config import SERVICES
from dss.core.utils import error


def remove_all_volumes() -> int:
    """Run ``compose down -v`` per service so each stack's ``.env`` files are loaded."""
    services = [
        name
        for name in sort_for_shutdown(SERVICES)
        if (Path(name) / "docker-compose.yml").is_file()
    ]
    failed: list[str] = []
    for service in services:
        print(f"ℹ️  Removing {service}...")
        result = subprocess.run([*get_compose_cmd(service), "down", "-v"])
        if result.returncode != 0:
            failed.append(service)
    if failed:
        error(f"Remove failed for: {', '.join(failed)}")
        return 1
    return 0


def main() -> None:
    sys.exit(remove_all_volumes())


if __name__ == "__main__":
    main()
