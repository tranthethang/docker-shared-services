import os
import subprocess
import argparse
import sys
from config import SERVICES, ACTIONS
from utils import print_header, success, error, warning

def is_valid_service(service):
    return service in SERVICES

def is_valid_action(action):
    return action in ACTIONS

def has_fzf():
    return subprocess.run(
        ["bash", "-lc", "command -v fzf >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0

# Two bridges cannot share one CIDR; adjacent /16s in 10/8.
SHARED_NETWORKS = (
    ("infra_shared", "10.0.0.0/16"),
    ("dev_tools", "10.1.0.0/16"),
)


def _docker_network_exists(name):
    return (
        subprocess.run(
            ["docker", "network", "inspect", name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def ensure_network():
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

def get_compose_cmd(service):
    return [
        "docker", "compose", 
        "-f", "docker-compose.shared.yml", 
        "-f", f"{service}/docker-compose.yml"
    ]

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
        ensure_network()
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
                ["bash", "-lc", f"printf '%s\n' \"$@\" | fzf --prompt='{title}> ' --height=20% --border"],
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
        print(f"  [{i+1}] {item}")
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
    parser = argparse.ArgumentParser(description='Docker Shared Services Manager')
    parser.add_argument('service', nargs='?', help='Service name')
    parser.add_argument('action', nargs='?', help='Action (up, down, restart, logs)')
    parser.add_argument('--list-services', action='store_true', help='List all available services')
    parser.add_argument('--list-actions', action='store_true', help='List all available actions')

    args = parser.parse_args()

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
