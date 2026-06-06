import subprocess
import argparse
import sys
from config import SERVICES, ACTIONS, START_ORDER
from utils import print_header, success, error, warning
from checkbox_menu import show_checkbox_menu

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

def is_service_running(service):
    result = subprocess.run(
        get_compose_cmd(service) + ["ps", "-q", "--status", "running"],
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())

def get_running_services():
    return [s for s in SERVICES if is_service_running(s)]

def sort_for_startup(services):
    order_map = {s: i for i, s in enumerate(START_ORDER)}
    return sorted(services, key=lambda s: (order_map.get(s, 999), s))

def sort_for_shutdown(services):
    order_map = {s: i for i, s in enumerate(START_ORDER)}

    def shutdown_key(service):
        if service == "traefik":
            return (-1, service)
        return (order_map.get(service, 500), service)

    return sorted(services, key=shutdown_key, reverse=True)

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
        for i, service in enumerate(SERVICES):
            mark = "x" if service in selected else " "
            running = " ● running" if service in default_set else ""
            print(f"  [{mark}] {i + 1:2}. {service}{running}")
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
        ensure_network()

    for service in to_up:
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

    if args.service == "manage" and not args.action:
        manage_services()
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
