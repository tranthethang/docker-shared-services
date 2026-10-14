"""Service manager entry point: ``python -m dss.cli.service [service] [action]``."""

import argparse
import subprocess
import sys

from dss.cli.compose import ensure_network, get_compose_cmd, validate_all_compose
from dss.cli.manage import manage_services
from dss.cli.readiness import ensure_dependencies_ready
from dss.core.config import ACTIONS, SERVICES
from dss.core.utils import error, print_header, success


def is_valid_service(service):
    return service in SERVICES


def is_valid_action(action):
    return action in ACTIONS


def has_fzf():
    return (
        subprocess.run(
            ["bash", "-lc", "command -v fzf >/dev/null 2>&1"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def execute_action(service, action):
    if not is_valid_service(service):
        error(f"Unknown service: {service}")
        print("\nAvailable services:")
        for i, s in enumerate(SERVICES):
            print(f"  {s:<15}", end="\n" if (i + 1) % 4 == 0 else "")
        print("\n")
        sys.exit(1)

    if not is_valid_action(action):
        error(f"Unknown action: {action}")
        print(f"Available actions: {', '.join(ACTIONS)}")
        sys.exit(1)

    cmd = get_compose_cmd(service)

    if action == "up":
        from dss.core.env_report import check_prerequisites

        if not check_prerequisites(service):
            error(f"Cannot start {service}: prerequisite checks failed.")
            sys.exit(1)
        ensure_network()
        if not ensure_dependencies_ready(service):
            sys.exit(1)
        success(f"Starting {service}...")
        subprocess.run(cmd + ["up", "-d"])
        success(f"{service} started successfully")
    elif action == "down":
        print(f"ℹ️  Stopping and removing {service}...")
        subprocess.run(cmd + ["down"])
        success(f"{service} down")
    elif action == "stop":
        print(f"ℹ️  Stopping {service}...")
        subprocess.run(cmd + ["stop"])
        success(f"{service} stopped")
    elif action == "restart":
        print(f"ℹ️  Restarting {service}...")
        subprocess.run(cmd + ["restart"])
        success(f"{service} restarted")
    elif action == "logs":
        print(f"ℹ️  Displaying logs for {service} (press Ctrl+C to exit)...")
        try:
            subprocess.run(cmd + ["logs", "-f"])
        except KeyboardInterrupt:
            print("\nStopped log streaming.")


def show_menu(items, title):
    if has_fzf():
        try:
            selected = subprocess.run(
                [
                    "bash",
                    "-lc",
                    f"printf '%s\n' \"$@\" | fzf --prompt='{title}> ' --height=20% --border",
                ],
                check=False,
                input="\n".join(items),
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ).stdout.strip()
            if selected:
                return selected
            sys.exit(0)
        except KeyboardInterrupt:
            sys.exit(0)

    print(f"ℹ️  {title}:")
    for i, item in enumerate(items):
        print(f"  [{i + 1}] {item}")
    print("")

    while True:
        try:
            choice = input(f"Select [1-{len(items)}] or [q]uit: ").strip().lower()
            if choice == "q":
                sys.exit(0)

            idx = int(choice) - 1
            if 0 <= idx < len(items):
                return items[idx]
            else:
                error(f"Invalid selection. Please enter 1-{len(items)} or 'q'")
        except ValueError:
            error(f"Invalid selection. Please enter 1-{len(items)} or 'q'")


def interactive_menu(preselected_action=None):
    print_header("Docker Shared Services Manager")

    service = show_menu(SERVICES, "Select service")
    print("")

    action = preselected_action or show_menu(ACTIONS, f"Select action for '{service}'")
    print("")

    execute_action(service, action)


def normalize_args(args):
    """
    Accept these forms:
    - <service> <action>
    - <action>                 (interactive pick service, action fixed)
    - (no args)                (interactive pick service, then action)
    """
    if not args.service and not args.action:
        return None, None

    # If only one positional was provided, argparse puts it in service.
    if args.service and not args.action:
        if is_valid_action(args.service) and not is_valid_service(args.service):
            return None, args.service
        return args.service, None

    return args.service, args.action


def main():
    parser = argparse.ArgumentParser(description="Docker Shared Services Manager")
    parser.add_argument("service", nargs="?", help="Service name")
    parser.add_argument("action", nargs="?", help="Action (up, down, restart, logs)")
    parser.add_argument("--list-services", action="store_true", help="List all available services")
    parser.add_argument("--list-actions", action="store_true", help="List all available actions")
    parser.add_argument(
        "--validate-compose",
        action="store_true",
        help="Validate each service compose file (loads service/.env)",
    )

    args = parser.parse_args()

    if args.service == "manage" and not args.action:
        manage_services()
        return

    if args.validate_compose:
        validate_all_compose()
        return

    if args.list_services:
        for s in SERVICES:
            print(s)
        return

    if args.list_actions:
        for a in ACTIONS:
            print(a)
        return

    service, action = normalize_args(args)

    if not service and not action:
        interactive_menu()
        return

    if not service and action:
        interactive_menu(preselected_action=action)
        return

    if service and not action:
        interactive_menu()
        return

    execute_action(service, action)


if __name__ == "__main__":
    main()
