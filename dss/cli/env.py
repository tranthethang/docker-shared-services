"""Command-line entry for env file management: ``python -m dss.cli.env <command>``."""

import argparse
import sys
from collections.abc import Callable

from dss.core.env_files import check_env, create_env, merge_missing_env_keys
from dss.core.env_report import check_prerequisites, show_summary, validate_env
from dss.core.secrets import fill_secrets, fill_shared_password


def main() -> None:
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

    if args.command in ("fill-shared-password", "passwords"):
        fill_shared_password(
            password=args.password,
            force=args.force,
            dry_run=args.dry_run,
        )
        return
    gates: dict[str, Callable[[str], bool]] = {
        "validate": validate_env,
        "check-prerequisites": check_prerequisites,
    }
    if args.command in gates:
        if not gates[args.command](args.service):
            sys.exit(1)
        return
    actions: dict[str, Callable[[str], object]] = {
        "check": check_env,
        "create": create_env,
        "merge-missing": merge_missing_env_keys,
        "fill-secrets": fill_secrets,
        "summary": show_summary,
    }
    actions[args.command](args.service)


if __name__ == "__main__":
    main()
