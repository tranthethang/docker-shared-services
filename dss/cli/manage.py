"""``make manage``: multi-select services, then start the selected and stop the rest."""

import subprocess
import sys

from dss.cli.checkbox_menu import show_checkbox_menu
from dss.cli.compose import (
    ensure_network,
    get_compose_cmd,
    get_running_services,
    sort_for_shutdown,
    sort_for_startup,
)
from dss.cli.readiness import ensure_dependencies_ready
from dss.core.config import SERVICES
from dss.core.utils import error, success


def _toggle_choices(choice: str, selected: set[str]) -> None:
    """Toggle each 1-based service number in ``choice``; report invalid parts."""
    invalid = False
    for part in choice.split():
        try:
            idx = int(part) - 1
        except ValueError:
            idx = -1
        if 0 <= idx < len(SERVICES):
            selected.symmetric_difference_update({SERVICES[idx]})
        else:
            error(f"Invalid selection: {part}")
            invalid = True
    if invalid:
        print("")


def _print_toggle_list(selected: set[str], running: set[str]) -> None:
    name_width = max(len(s) for s in SERVICES) + 2
    for i, service in enumerate(SERVICES):
        mark = "x" if service in selected else " "
        badge = " ● running" if service in running else ""
        print(f"  {i + 1:2}. {service:<{name_width}} [{mark}]{badge}")
    print("")


def show_multi_select(default_selected: list[str]) -> list[str]:
    default_set = set(default_selected)
    title = "Docker Shared Services — Manage"

    chosen = show_checkbox_menu(
        SERVICES,
        default_checked=default_selected,
        title=title,
        badge_fn=lambda s: " ● running" if s in default_set else "",
    )

    if chosen is not None:
        return chosen

    # Non-TTY fallback (e.g. piped input)
    selected = set(default_set)
    print("ℹ️  Toggle services (running services are pre-selected):")
    print("   Enter number(s) to toggle, empty line to confirm, q to quit")
    print("")

    while True:
        _print_toggle_list(selected, default_set)
        try:
            choice = input("Toggle (numbers) or Enter to confirm [q]: ").strip().lower()
        except KeyboardInterrupt:
            print("")
            sys.exit(0)

        if choice == "q":
            sys.exit(0)
        if choice == "":
            return sorted(selected, key=SERVICES.index)
        _toggle_choices(choice, selected)


def confirm_apply(to_up: list[str], to_down: list[str]) -> bool:
    if not to_up and not to_down:
        print("ℹ️  No changes needed.")
        return False

    print("")
    if to_up:
        print(f"  Will start:  {', '.join(to_up)}")
    if to_down:
        print(f"  Will stop:   {', '.join(to_down)}")
    print("")

    try:
        reply = input("Apply changes? [Y/n] ").strip().lower()
    except KeyboardInterrupt:
        print("")
        sys.exit(0)

    return reply in ("", "y", "yes")


def apply_manage_changes(selected: list[str]) -> None:
    running = set(get_running_services())
    selected_set = set(selected)

    to_up = sort_for_startup(selected_set - running)
    to_down = sort_for_shutdown(running - selected_set)

    if not confirm_apply(to_up, to_down):
        print("Operation cancelled")
        return

    run_manage_plan(to_up, to_down)


def run_manage_plan(to_up: list[str], to_down: list[str]) -> None:
    """Start ``to_up`` and stop ``to_down`` with Compose output on the terminal."""
    failed: list[str] = []

    for service in to_down:
        cmd = get_compose_cmd(service)
        print(f"ℹ️  Stopping and removing {service}...")
        result = subprocess.run([*cmd, "down"])
        if result.returncode == 0:
            success(f"{service} down")
        else:
            error(f"Failed to stop {service}")
            failed.append(service)

    if to_up:
        from dss.core.env_report import check_prerequisites

        invalid = [s for s in to_up if not check_prerequisites(s)]
        if invalid:
            error(f"Cannot start services: prerequisite checks failed for {', '.join(invalid)}")
            sys.exit(1)
        ensure_network()

    for service in to_up:
        if not ensure_dependencies_ready(service):
            failed.append(service)
            break
        cmd = get_compose_cmd(service)
        success(f"Starting {service}...")
        result = subprocess.run([*cmd, "up", "-d"])
        if result.returncode == 0:
            success(f"{service} started successfully")
        else:
            error(f"Failed to start {service}")
            failed.append(service)

    print("")
    if failed:
        error(f"Completed with errors: {', '.join(failed)}")
        sys.exit(1)
    success("All changes applied successfully")


def manage_services() -> None:
    print("ℹ️  Detecting running services...")
    running = get_running_services()
    if running:
        print(f"   Running: {', '.join(running)}")
    else:
        print("   No services are currently running")
    print("")

    selected = show_multi_select(running)
    print("")
    apply_manage_changes(selected)
