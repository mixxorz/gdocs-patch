"""Command-line interface for gdocs-patch."""

import argparse
import json
import sys
import textwrap
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import cast

from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]

from gdocs_patch.client import (
    AuthenticationError,
    GoogleDocsClient,
    load_credentials,
    login,
)
from gdocs_patch.commands import (
    XhtmlEdit,
    XhtmlEditError,
    describe_skill,
    describe_syntax,
    edit_document,
    read_document,
    write_document,
)
from gdocs_patch.compiler import UnsupportedTransformation
from gdocs_patch.xhtml import XHTMLParseError


class InputError(Exception):
    """Raised when command input is invalid."""


def _read_text(source: Path) -> str:
    try:
        if source == Path("-"):
            return sys.stdin.read()
        return source.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        location = "standard input" if source == Path("-") else str(source)
        raise InputError(f"Could not read {location}: {error}") from None


def _read_json_object(source: Path) -> dict[str, object]:
    try:
        value = json.loads(_read_text(source))
    except (ValueError, RecursionError):
        raise InputError("Input must contain one valid JSON object.") from None
    if not isinstance(value, dict):
        raise InputError("Input must be a JSON object.")
    return cast(dict[str, object], value)


def _write_text(output: Path | None, content: str) -> None:
    if output is None:
        sys.stdout.write(content)
        return
    try:
        output.write_text(content, encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise InputError(f"Could not write {output}: {error}") from None


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

    read_parser = commands.add_parser(
        "read",
        help="Read a Google document as canonical XHTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              gdocs-patch read DOCUMENT_ID
              gdocs-patch read DOCUMENT_ID --output document.xhtml
              gdocs-patch read DOCUMENT_ID --offset 8 --limit 4

            Output is complete canonical XHTML by default. --offset selects the
            first line to return (1-indexed), and --limit bounds the number of lines.
            """
        ),
    )
    read_parser.add_argument("document_id", metavar="DOCUMENT_ID")
    read_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Write XHTML to this file instead of standard output.",
    )
    read_parser.add_argument(
        "--offset",
        type=int,
        default=1,
        help="Line number to start reading from (1-indexed).",
    )
    read_parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of XHTML lines to return.",
    )

    edit_parser = commands.add_parser(
        "edit",
        help="Edit exact text in canonical XHTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            EDITS_FILE must contain one JSON object:
              {"edits":[{"oldText":"old","newText":"new"}]}

            Use - as EDITS_FILE to read the JSON object from standard input.

            Examples:
              gdocs-patch edit DOCUMENT_ID edits.json
              gdocs-patch edit DOCUMENT_ID - < edits.json
            """
        ),
    )
    edit_parser.add_argument("document_id", metavar="DOCUMENT_ID")
    edit_parser.add_argument("input", metavar="EDITS_FILE", type=Path)
    edit_parser.add_argument(
        "--allow-bullet-normalization",
        action="store_true",
        help="Allow customized lists to use the closest supported preset.",
    )

    write_parser = commands.add_parser(
        "write",
        help="Write canonical XHTML to a Google document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Start with complete XHTML produced by `gdocs-patch read` and preserve
            unrelated document structure and metadata. Use - as XHTML_FILE to read
            the document from standard input.

            Examples:
              gdocs-patch write DOCUMENT_ID document.xhtml
              gdocs-patch write DOCUMENT_ID - < document.xhtml
            """
        ),
    )
    write_parser.add_argument("document_id", metavar="DOCUMENT_ID")
    write_parser.add_argument("input", metavar="XHTML_FILE", type=Path)
    write_parser.add_argument(
        "--allow-bullet-normalization",
        action="store_true",
        help="Allow customized lists to use the closest supported preset.",
    )

    syntax_parser = commands.add_parser(
        "syntax",
        help="Explore the XHTML document syntax.",
    )
    syntax_parser.add_argument(
        "syntax_topic",
        nargs="?",
        choices=("paragraphs", "lists", "tables", "equations", "sections"),
        help="Show syntax for one supported content type.",
    )
    syntax_parser.add_argument(
        "--reference",
        action="store_true",
        help="Show the detailed reference for a content type.",
    )

    commands.add_parser(
        "skill",
        help="Show best practices for coding agents using gdocs-patch.",
    )

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

    if args.command == "skill":
        sys.stdout.write(describe_skill())
        return 0

    if args.command == "syntax":
        if args.reference and args.syntax_topic is None:
            parser.error("--reference requires TOPIC")
        sys.stdout.write(
            describe_syntax(
                args.syntax_topic,
                reference=args.reference,
            )
        )
        return 0

    if args.command == "read":
        try:
            if args.offset < 1:
                raise InputError("Read command offset must be an integer >= 1.")
            if args.limit is not None and args.limit <= 0:
                raise InputError("Read command limit must be an integer > 0.")

            client = GoogleDocsClient(credentials=load_credentials())
            output = read_document(
                client=client,
                doc_id=args.document_id,
                offset=args.offset,
                limit=args.limit,
            )
            _write_text(args.output, output)
        except (InputError, AuthenticationError, GoogleAuthError, HttpError) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        return 0

    if args.command == "write":
        try:
            content = _read_text(args.input)
            client = GoogleDocsClient(credentials=load_credentials())
            write_document(
                client=client,
                doc_id=args.document_id,
                content=content,
                allow_bullet_normalization=args.allow_bullet_normalization,
            )
        except (
            InputError,
            XHTMLParseError,
            UnsupportedTransformation,
            AuthenticationError,
            GoogleAuthError,
            HttpError,
        ) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        print(f"Successfully wrote to {args.document_id}.")
        return 0

    if args.command == "edit":
        try:
            input_object = _read_json_object(args.input)
            unknown_fields = input_object.keys() - {"edits"}
            if unknown_fields:
                field = sorted(unknown_fields)[0]
                raise InputError(f"Edit command input has unknown field: {field}.")

            input_edits = input_object.get("edits")
            if not isinstance(input_edits, list):
                raise InputError("Edit command input requires array field: edits.")

            edits: list[XhtmlEdit] = []
            for edit_index, input_edit_value in enumerate(
                cast(list[object], input_edits)
            ):
                if not isinstance(input_edit_value, dict):
                    raise InputError(
                        f"Edit command edits[{edit_index}] must be an object."
                    )
                input_edit = cast(dict[str, object], input_edit_value)
                edit_fields = input_edit.keys()
                if edit_fields != {"oldText", "newText"}:
                    raise InputError(
                        f"Edit command edits[{edit_index}] requires exactly "
                        "oldText and newText."
                    )
                old_text = input_edit["oldText"]
                new_text = input_edit["newText"]
                if not isinstance(old_text, str) or not isinstance(new_text, str):
                    raise InputError(
                        f"Edit command edits[{edit_index}].oldText and "
                        f"edits[{edit_index}].newText must be strings."
                    )
                edits.append(XhtmlEdit(old_text=old_text, new_text=new_text))

            if not edits:
                raise InputError(
                    "Edit command input is invalid. edits must contain at least one "
                    "replacement."
                )
            for edit_index, edit in enumerate(edits):
                if not edit.old_text:
                    raise InputError(
                        f"edits[{edit_index}].oldText must not be empty in "
                        f"{args.document_id}."
                    )

            client = GoogleDocsClient(credentials=load_credentials())
            count = edit_document(
                client=client,
                doc_id=args.document_id,
                edits=edits,
                allow_bullet_normalization=args.allow_bullet_normalization,
            )
        except (
            InputError,
            XhtmlEditError,
            XHTMLParseError,
            UnsupportedTransformation,
            AuthenticationError,
            GoogleAuthError,
            HttpError,
        ) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        noun = "block" if count == 1 else "blocks"
        print(f"Successfully replaced {count} {noun} in {args.document_id}.")
        return 0

    parser.print_help()
    return 0
