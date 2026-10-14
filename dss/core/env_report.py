"""Validate ``.env`` files and print the configuration summary."""

import os

from dss.core.config import (
    AUTH_GATEWAY_MIDDLEWARE_OFF,
    AUTH_GATEWAY_MIDDLEWARES_ON,
    AUTH_OPT_IN_UI_SERVICES,
    INVALID_PASSWORD_VALUES,
    SERVICE_INFO_VARS,
    STRONG_PASSWORD_REQUIRED,
    VALIDATION_RULES,
)
from dss.core.env_files import get_services
from dss.core.utils import (
    error,
    print_header,
    read_env_value,
    success,
    validate_password_strength,
)


def validate_env(service_arg):
    services = get_services(service_arg)
    print("\nValidating environment variables...\n")
    errors = 0
    for s in services:
        env_path = os.path.join(s, ".env")
        if not os.path.exists(env_path):
            continue

        for var in VALIDATION_RULES.get(s, []):
            value = read_env_value(env_path, var)
            if value is None:
                error(f"{s}: Missing {var} variable")
                errors += 1
            elif not value:
                error(f"{s}: {var} is empty (set a value in {s}/.env)")
                errors += 1
            elif value in INVALID_PASSWORD_VALUES:
                error(
                    f"{s}: {var} has placeholder/insecure value '{value}' (run make setup or set a secure value)"
                )
                errors += 1
            else:
                success(f"{s}: {var} configured")

    if errors > 0:
        print(f"\n❌ Found {errors} validation errors")
        return False
    print("\n✅ All environment variables validated!")
    return True


def check_prerequisites(service_arg="all") -> bool:
    """
    Check if environment files exist and mandatory variables are set before starting services.
    Returns True if valid, False if errors found.
    """
    if not os.path.exists(".env"):
        error("Root environment file (.env) not found.")
        print("  Remediation: Run 'make setup' to initialize .env from .env.example.\n")
        return False

    services = get_services(service_arg)
    errors = 0
    for s in services:
        if s == ".":
            continue
        env_path = os.path.join(s, ".env")
        if not os.path.exists(env_path):
            error(f"{s}: Environment file not found ({env_path}).")
            print(f"  Remediation: Run 'make setup' or copy {s}/.env.example to {env_path}.\n")
            errors += 1
            continue

        for var in VALIDATION_RULES.get(s, []):
            val = read_env_value(env_path, var)
            if not val or val in INVALID_PASSWORD_VALUES:
                error(
                    f"{s}: Mandatory variable {var} is unset or contains placeholder in {env_path}."
                )
                print(
                    f"  Remediation: Run 'make setup' to generate credentials or configure {var} in {env_path}.\n"
                )
                errors += 1

        for var in STRONG_PASSWORD_REQUIRED.get(s, []):
            val = read_env_value(env_path, var)
            problem = validate_password_strength(val) if val else None
            if problem:
                error(f"{s}: {var} in {env_path} is too weak. {problem}")
                print(
                    "  Remediation: rotate the shared password "
                    "(see 'Rotate the shared password' in docs/troubleshooting.md).\n"
                )
                errors += 1

    return errors == 0


def show_summary(service_arg):
    services = get_services(service_arg)
    print_header("Services Configuration")
    for s in services:
        if s == ".":
            continue
        env_path = os.path.join(s, ".env")
        if not os.path.exists(env_path):
            continue
        print(f"Service: {s}")
        vars_to_check = SERVICE_INFO_VARS.get(s, [])
        if not vars_to_check and s == "traefik":
            print("  Ports: 80, 443")
        elif not vars_to_check:
            print("  (configured)")
        else:
            found = False
            with open(env_path) as f:
                for line in f:
                    for var in vars_to_check:
                        if line.startswith(f"{var}="):
                            print(f"  {line.strip()}")
                            found = True
            if not found:
                print("  (no specific ports configured in .env)")
        if s in AUTH_OPT_IN_UI_SERVICES:
            enabled = (read_env_value(env_path, "AUTH_ENABLED") or "false").lower()
            middleware = (read_env_value(env_path, "AUTH_MIDDLEWARE") or "").strip()
            effective = middleware or AUTH_GATEWAY_MIDDLEWARE_OFF
            state = "on" if effective in AUTH_GATEWAY_MIDDLEWARES_ON else "off"
            print(
                f"  AUTH gateway: {state} "
                f"(AUTH_ENABLED={enabled}, AUTH_MIDDLEWARE={middleware or AUTH_GATEWAY_MIDDLEWARE_OFF})"
            )
        print("")
