"""Command-line interface for gdocs-patch."""

import argparse
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path

from gdocs_patch.client import AuthenticationError, login


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="gdocs-patch",
        description="Apply structured patches to Google Docs.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {version('gdocs-patch')}",
    )

    commands = parser.add_subparsers(dest="command")
    auth_parser = commands.add_parser("auth", help="Manage Google authentication.")
    auth_commands = auth_parser.add_subparsers(dest="auth_command", required=True)
    login_parser = auth_commands.add_parser(
        "login",
        help="Log in with Google OAuth.",
    )
    login_parser.add_argument(
        "--client-secrets",
        type=Path,
        help=(
            "Google desktop OAuth client JSON; defaults to "
            "~/.config/gdocs-patch/client_secret.json."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "auth" and args.auth_command == "login":
        try:
            credentials_path = login(client_secrets=args.client_secrets)
        except AuthenticationError as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        print(f"Credentials saved to {credentials_path}")
        return 0

    parser.print_help()
    return 0
