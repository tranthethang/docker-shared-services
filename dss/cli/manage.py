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


def show_multi_select(default_selected):
    default_set = set(default_selected)
    title = "Docker Shared Services — Manage"

    selected = show_checkbox_menu(
        SERVICES,
        default_checked=default_selected,
        title=title,
        badge_fn=lambda s: " ● running" if s in default_set else "",
    )

    if selected is not None:
        return selected

    # Non-TTY fallback (e.g. piped input)
    selected = set(default_set)
    print("ℹ️  Toggle services (running services are pre-selected):")
    print("   Enter number(s) to toggle, empty line to confirm, q to quit")
    print("")

    while True:
        name_width = max(len(s) for s in SERVICES) + 2
        for i, service in enumerate(SERVICES):
            mark = "x" if service in selected else " "
            running = " ● running" if service in default_set else ""
            print(f"  {i + 1:2}. {service:<{name_width}} [{mark}]{running}")
        print("")

        try:
            choice = input("Toggle (numbers) or Enter to confirm [q]: ").strip().lower()
        except KeyboardInterrupt:
            print("")
            sys.exit(0)

        if choice == "q":
            sys.exit(0)
        if choice == "":
            return sorted(selected, key=SERVICES.index)

        invalid = False
        for part in choice.split():
            try:
                idx = int(part) - 1
                if 0 <= idx < len(SERVICES):
                    service = SERVICES[idx]
                    if service in selected:
                        selected.discard(service)
                    else:
                        selected.add(service)
                else:
                    error(f"Invalid selection: {part}")
                    invalid = True
            except ValueError:
                error(f"Invalid selection: {part}")
                invalid = True

        if invalid:
            print("")


def confirm_apply(to_up, to_down):
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


def apply_manage_changes(selected):
    running = set(get_running_services())
    selected_set = set(selected)

    to_up = sort_for_startup(selected_set - running)
    to_down = sort_for_shutdown(running - selected_set)

    if not confirm_apply(to_up, to_down):
        print("Operation cancelled")
        return

    failed = []

    for service in to_down:
        cmd = get_compose_cmd(service)
        print(f"ℹ️  Stopping and removing {service}...")
        result = subprocess.run(cmd + ["down"])
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
        result = subprocess.run(cmd + ["up", "-d"])
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


def manage_services():
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
