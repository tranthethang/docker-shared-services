import os
import shutil
import argparse
from config import SERVICES, VALIDATION_RULES, SERVICE_INFO_VARS
from utils import print_header, success, warning, error, generate_password

def get_services(service_arg):
    if not service_arg or service_arg == "all":
        return ["."] + SERVICES
    if service_arg in SERVICES or service_arg == ".":
        return [service_arg]
    return []

def check_env(service_arg):
    services = get_services(service_arg)
    print("Checking .env files...\n")
    missing = []
    for s in services:
        env_path = os.path.join(s, ".env")
        example_path = os.path.join(s, ".env.example")
        if os.path.exists(env_path):
            success(f"{s}/.env exists")
        elif os.path.exists(example_path):
            warning(f"{s}/.env missing (only .env.example exists)")
            missing.append(s)
        else:
            error(f"{s}/.env.example not found")
    
    if missing:
        print(f"\nFound {len(missing)} services missing .env files")
        # Note: Interactive prompt handled by shell script to keep python logic clean
        return True
    return False

def create_env(service_arg):
    services = get_services(service_arg)
    print("\nCreating .env files from .env.example...\n")
    for s in services:
        env_path = os.path.join(s, ".env")
        example_path = os.path.join(s, ".env.example")
        if os.path.exists(example_path) and not os.path.exists(env_path):
            shutil.copy(example_path, env_path)
            success(f"Created {s}/.env")
    print("\n✅ .env files created successfully!")
    warning("Remember to update password and sensitive values in .env files!")

def validate_env(service_arg):
    services = get_services(service_arg)
    print("\nValidating environment variables...\n")
    errors = 0
    for s in services:
        env_path = os.path.join(s, ".env")
        if not os.path.exists(env_path):
            continue
        
        rules = VALIDATION_RULES.get(s, [])
        with open(env_path, 'r') as f:
            content = f.read()
            for var in rules:
                if var not in content:
                    error(f"{s}: Missing {var} variable")
                    errors += 1
                else:
                    success(f"{s}: {var} configured")
    
    if errors > 0:
        print(f"\n❌ Found {errors} validation errors")
        return False
    else:
        print("\n✅ All environment variables validated!")
        return True

def show_summary(service_arg):
    services = get_services(service_arg)
    print_header("Services Configuration")
    for s in services:
        if s == ".":
            continue
        env_path = os.path.join(s, ".env")
        if os.path.exists(env_path):
            print(f"Service: {s}")
            vars_to_check = SERVICE_INFO_VARS.get(s, [])
            if not vars_to_check and s == "traefik":
                print("  Ports: 80, 443, 8080")
            elif not vars_to_check:
                print("  (configured)")
            else:
                found = False
                with open(env_path, 'r') as f:
                    for line in f:
                        for var in vars_to_check:
                            if var in line:
                                print(f"  {line.strip()}")
                                found = True
                if not found:
                    print("  (no specific ports configured in .env)")
            print("")

def main():
    parser = argparse.ArgumentParser(description='Docker Services Environment Manager')
    parser.add_argument('command', choices=['check', 'create', 'validate', 'summary', 'passwords'])
    parser.add_argument('service', nargs='?', default='all')
    
    args = parser.parse_args()
    
    if args.command == 'check':
        check_env(args.service)
    elif args.command == 'create':
        create_env(args.service)
    elif args.command == 'validate':
        if not validate_env(args.service):
            exit(1)
    elif args.command == 'summary':
        show_summary(args.service)
    elif args.command == 'passwords':
        print("\nGenerating strong passwords...\n")
        print("Generated strong passwords (save these):\n")
        print(f"PASSWORD_102: {generate_password()}")
        print("\nYou can update .env files with these passwords")

if __name__ == "__main__":
    main()
