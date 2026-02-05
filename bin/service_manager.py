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

def ensure_network():
    try:
        subprocess.run(["docker", "network", "inspect", "dev_tools"], 
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("ℹ️  Creating network dev_tools...")
        subprocess.run(["docker", "network", "create", "dev_tools", 
                        "--subnet", "10.0.0.0/16", "--driver", "bridge"], check=True)
        success("Network dev_tools created")

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
        print(f"ℹ️  Stopping {service}...")
        subprocess.run(cmd + ["down"])
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

    if not args.service or not args.action:
        # If arguments are missing, we return a special exit code so the bash script
        # can handle the interactive menu.
        sys.exit(2)

    execute_action(args.service, args.action)

if __name__ == "__main__":
    main()
