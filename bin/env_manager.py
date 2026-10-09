import argparse
import os
import shutil

from config import (
    AUTH_GATEWAY_MIDDLEWARE_OFF,
    AUTH_GATEWAY_MIDDLEWARES_ON,
    AUTH_OPT_IN_UI_SERVICES,
    AUTO_GENERATED_SECRETS,
    SERVICE_INFO_VARS,
    SERVICES,
    SHARED_PASSWORD_KEYS,
    SHARED_PASSWORD_PLACEHOLDERS,
    SHARED_PASSWORD_TEMPLATES,
    VALIDATION_RULES,
)
from utils import (
    error,
    generate_password,
    generate_secret,
    iter_env_assignments,
    print_header,
    read_env_value,
    set_env_value,
    success,
    warning,
)


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
        return True
    return False


def create_env(service_arg):
    services = get_services(service_arg)
    print("\nCreating .env files from .env.example...\n")
    created = []
    for s in services:
        env_path = os.path.join(s, ".env")
        example_path = os.path.join(s, ".env.example")
        if os.path.exists(example_path) and not os.path.exists(env_path):
            shutil.copy(example_path, env_path)
            success(f"Created {s}/.env")
            created.append(s)
    if created:
        print("\n✅ .env files created successfully!")
    else:
        print("\n✅ No missing .env files to create.")
    warning("Next: shared password sync (fill-shared-password) + unique secrets (fill-secrets).")


def _example_env_assignments(example_path: str) -> list[tuple[str, str]]:
    """Return (KEY, raw_value) pairs from .env.example in file order (first wins)."""
    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    for key, value in iter_env_assignments(example_path):
        if key in seen:
            continue
        seen.add(key)
        pairs.append((key, value))
    return pairs


def merge_missing_env_keys(service_arg):
    """Append keys that exist in .env.example but are absent from .env.

    Never overwrites existing keys (including empty values). Safe for repeated
    `make setup` after .env.example gains new variables (e.g. AUTH_*).
    """
    services = get_services(service_arg)
    print("\nMerging missing keys from .env.example into existing .env files...\n")
    added_total = 0
    for s in services:
        env_path = os.path.join(s, ".env")
        example_path = os.path.join(s, ".env.example")
        if not os.path.exists(env_path) or not os.path.exists(example_path):
            continue
        missing = [
            (key, value)
            for key, value in _example_env_assignments(example_path)
            if read_env_value(env_path, key) is None
        ]
        if not missing:
            continue
        with open(env_path) as f:
            content = f.read()
        suffix_parts = []
        if content and not content.endswith("\n"):
            suffix_parts.append("\n")
        if content.strip():
            suffix_parts.append("\n")
        for key, value in missing:
            suffix_parts.append(f"{key}={value}\n")
            success(f"{s}: added {key}")
            added_total += 1
        with open(env_path, "a") as f:
            f.write("".join(suffix_parts))
    if added_total == 0:
        print("✅ No missing keys to merge.")
    else:
        print(f"\n✅ Added {added_total} missing key(s) from .env.example.")


def fill_secrets(service_arg):
    """Fill empty AUTO_GENERATED_SECRETS values; leave existing non-empty values alone."""
    services = get_services(service_arg)
    print("\nFilling empty auto-generated secrets...\n")
    filled = 0
    for s in services:
        if s == ".":
            continue
        env_path = os.path.join(s, ".env")
        specs = AUTO_GENERATED_SECRETS.get(s)
        if not specs or not os.path.exists(env_path):
            continue
        for var, (method, nbytes) in specs.items():
            current = read_env_value(env_path, var)
            if current:
                success(f"{s}: {var} already set (left unchanged)")
                continue
            value = generate_secret(method, nbytes)
            set_env_value(env_path, var, value)
            success(f"{s}: generated {var}")
            filled += 1

    if filled == 0:
        print("✅ No empty auto-generated secrets to fill.")
    else:
        print(f"\n✅ Generated {filled} secret value(s).")


def _resolve_shared_password(explicit: str | None) -> str:
    """
    Resolve the single shared password.

    Priority:
      1. explicit --password
      2. DSS_SHARED_PASSWORD environment variable (non-empty)
      3. Existing non-empty DSS_SHARED_PASSWORD in root .env (including Password102!
         if the user chose it previously)
      4. Fresh random password
    """
    if explicit:
        return explicit
    from_env = os.environ.get("DSS_SHARED_PASSWORD", "").strip()
    if from_env:
        return from_env
    if os.path.exists(".env"):
        root_existing = read_env_value(".env", "DSS_SHARED_PASSWORD")
        if root_existing:
            return root_existing
    return generate_password()


def _should_overwrite(current: str | None, force: bool) -> bool:
    if force:
        return True
    if current is None:
        return True
    if current in SHARED_PASSWORD_PLACEHOLDERS:
        return True
    # Compound defaults that still embed the repo placeholder.
    if "Password102!" in current:
        return True
    return False


def fill_shared_password(
    password: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """
    Apply ONE shared password to every SHARED_PASSWORD_KEYS entry.

    Resolution order for the password value:
      1. --password / explicit argument
      2. DSS_SHARED_PASSWORD environment variable
      3. Existing non-placeholder DSS_SHARED_PASSWORD in root .env
      4. Fresh random password (generate_password)

    By default only placeholders (Password102!, empty, known change-me values)
    are overwritten. Use force=True to rewrite all listed keys.
    """
    resolved = _resolve_shared_password(password)
    print("\nApplying shared password across services...\n")
    if password:
        success("Using password from --password")
    elif os.environ.get("DSS_SHARED_PASSWORD", "").strip():
        success("Using password from DSS_SHARED_PASSWORD env")
    elif os.path.exists(".env") and read_env_value(".env", "DSS_SHARED_PASSWORD"):
        success("Reusing DSS_SHARED_PASSWORD from root .env")
    else:
        success("Generated a new random shared password")

    if dry_run:
        warning(f"Dry-run: would set shared password ({len(resolved)} chars)")
    else:
        # Ensure root .env exists so we can record DSS_SHARED_PASSWORD.
        if not os.path.exists(".env") and os.path.exists(".env.example"):
            shutil.copy(".env.example", ".env")
            success("Created ./.env from .env.example")

    updated = 0
    skipped = 0

    for service, keys in SHARED_PASSWORD_KEYS.items():
        env_path = os.path.join(service, ".env") if service != "." else ".env"
        if not os.path.exists(env_path):
            continue
        for key in keys:
            current = read_env_value(env_path, key)
            if not _should_overwrite(current, force):
                skipped += 1
                continue
            if dry_run:
                print(f"  would set {env_path}: {key}")
            else:
                set_env_value(env_path, key, resolved)
                success(f"{env_path}: {key}")
            updated += 1

    for (service, key), template in SHARED_PASSWORD_TEMPLATES.items():
        env_path = os.path.join(service, ".env") if service != "." else ".env"
        if not os.path.exists(env_path):
            continue
        current = read_env_value(env_path, key)
        if not _should_overwrite(current, force):
            skipped += 1
            continue
        value = template.format(password=resolved)
        if dry_run:
            print(f"  would set {env_path}: {key}")
        else:
            set_env_value(env_path, key, value)
            success(f"{env_path}: {key}")
        updated += 1

    print(f"\n✅ Shared password sync complete (updated={updated}, skipped_custom={skipped}).")
    if not dry_run:
        warning(
            "Same password is used for all listed services. "
            "Unique secrets (Garage, Woodpecker agent, Zitadel masterkey) "
            "are handled separately by fill-secrets."
        )
        print(
            "\nTo keep using Password102! next time:\n"
            "  make setup password='Password102!'\n"
            "  # or: DSS_SHARED_PASSWORD='Password102!' make setup\n"
        )
    return resolved


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
            else:
                success(f"{s}: {var} configured")

    if errors > 0:
        print(f"\n❌ Found {errors} validation errors")
        return False
    print("\n✅ All environment variables validated!")
    return True


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
            print("  Ports: 80, 443, 8080")
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


def main():
    parser = argparse.ArgumentParser(description="Docker Services Environment Manager")
    parser.add_argument(
        "command",
        choices=[
            "check",
            "create",
            "merge-missing",
            "fill-secrets",
            "fill-shared-password",
            "validate",
            "summary",
            "passwords",
        ],
    )
    parser.add_argument("service", nargs="?", default="all")
    parser.add_argument(
        "--password",
        default=None,
        help="Shared password to apply (default: DSS_SHARED_PASSWORD env, "
        "else existing root .env value, else generate).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite even non-placeholder password values.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files.",
    )

    args = parser.parse_args()

    if args.command == "check":
        check_env(args.service)
    elif args.command == "create":
        create_env(args.service)
    elif args.command == "merge-missing":
        merge_missing_env_keys(args.service)
    elif args.command == "fill-secrets":
        fill_secrets(args.service)
    elif args.command in ("fill-shared-password", "passwords"):
        fill_shared_password(
            password=args.password,
            force=args.force,
            dry_run=args.dry_run,
        )
    elif args.command == "validate":
        if not validate_env(args.service):
            exit(1)
    elif args.command == "summary":
        show_summary(args.service)


if __name__ == "__main__":
    main()
