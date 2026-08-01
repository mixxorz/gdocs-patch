"""Command-line interface for gdocs-patch."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
