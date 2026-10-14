"""Command-line entry for env file management: ``python -m dss.cli.env <command>``."""

import argparse

from dss.core.env_files import check_env, create_env, merge_missing_env_keys
from dss.core.env_report import check_prerequisites, show_summary, validate_env
from dss.core.secrets import fill_secrets, fill_shared_password


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
            "check-prerequisites",
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
    elif args.command == "check-prerequisites":
        if not check_prerequisites(args.service):
            exit(1)
    elif args.command == "summary":
        show_summary(args.service)


if __name__ == "__main__":
    main()
