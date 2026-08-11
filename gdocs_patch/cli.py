"""Command-line interface for gdocs-patch."""

import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import cast

from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]

from gdocs_patch.client import (
    AuthenticationError,
    GoogleDocsClient,
    load_credentials,
    login,
)
from gdocs_patch.commands import XhtmlEdit, edit_document, read_document, write_document
from gdocs_patch.compiler import UnsupportedTransformation
from gdocs_patch.xhtml import XHTMLParseError


class InputError(Exception):
    """Raised when command input is invalid."""


def _read_json_object() -> dict[str, object]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise InputError("Input must contain one valid JSON object.") from None
    if not isinstance(value, dict):
        raise InputError("Input must be a JSON object.")
    return cast(dict[str, object], value)


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
    commands.add_parser("read", help="Read a Google document as canonical XHTML.")
    commands.add_parser("write", help="Write canonical XHTML to a Google document.")
    commands.add_parser("edit", help="Edit exact text in canonical XHTML.")
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

    if args.command == "read":
        try:
            input_object = _read_json_object()
            unknown_fields = input_object.keys() - {"docId", "offset", "limit"}
            if unknown_fields:
                field = sorted(unknown_fields)[0]
                raise InputError(f"Read command input has unknown field: {field}.")

            doc_id = input_object.get("docId")
            if not isinstance(doc_id, str):
                raise InputError("Read command input requires string field: docId.")

            offset = input_object.get("offset", 1)
            if type(offset) is not int or offset < 1:
                raise InputError("Read command input offset must be an integer >= 1.")

            limit = input_object.get("limit")
            if "limit" in input_object and (type(limit) is not int or limit <= 0):
                raise InputError("Read command input limit must be an integer > 0.")

            client = GoogleDocsClient(credentials=load_credentials())
            output = read_document(
                client=client,
                doc_id=doc_id,
                offset=offset,
                limit=cast(int | None, limit),
            )
        except (InputError, AuthenticationError, HttpError) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        sys.stdout.write(output)
        return 0

    if args.command == "write":
        try:
            input_object = _read_json_object()
            unknown_fields = input_object.keys() - {"docId", "content"}
            if unknown_fields:
                field = sorted(unknown_fields)[0]
                raise InputError(f"Write command input has unknown field: {field}.")

            doc_id = input_object.get("docId")
            if not isinstance(doc_id, str):
                raise InputError("Write command input requires string field: docId.")

            content = input_object.get("content")
            if not isinstance(content, str):
                raise InputError("Write command input requires string field: content.")

            client = GoogleDocsClient(credentials=load_credentials())
            write_document(client=client, doc_id=doc_id, content=content)
        except (
            InputError,
            XHTMLParseError,
            UnsupportedTransformation,
            AuthenticationError,
            HttpError,
        ) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        print(f"Successfully wrote to {doc_id}.")
        return 0

    if args.command == "edit":
        try:
            input_object = _read_json_object()
            unknown_fields = input_object.keys() - {"docId", "edits"}
            if unknown_fields:
                field = sorted(unknown_fields)[0]
                raise InputError(f"Edit command input has unknown field: {field}.")

            doc_id = input_object.get("docId")
            if not isinstance(doc_id, str):
                raise InputError("Edit command input requires string field: docId.")

            input_edits = input_object.get("edits")
            if not isinstance(input_edits, list):
                raise InputError("Edit command input requires array field: edits.")

            edits: list[XhtmlEdit] = []
            for input_edit_value in cast(list[object], input_edits):
                if not isinstance(input_edit_value, dict):
                    raise InputError("Edit command edits must contain objects.")
                input_edit = cast(dict[str, object], input_edit_value)
                edit_fields = input_edit.keys()
                if edit_fields != {"oldText", "newText"}:
                    raise InputError(
                        "Edit command edits require exactly oldText and newText."
                    )
                old_text = input_edit["oldText"]
                new_text = input_edit["newText"]
                if not isinstance(old_text, str) or not isinstance(new_text, str):
                    raise InputError(
                        "Edit command oldText and newText must be strings."
                    )
                edits.append(XhtmlEdit(old_text=old_text, new_text=new_text))

            client = GoogleDocsClient(credentials=load_credentials())
            count = edit_document(client=client, doc_id=doc_id, edits=edits)
        except (
            InputError,
            XHTMLParseError,
            UnsupportedTransformation,
            AuthenticationError,
            HttpError,
        ) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        noun = "block" if count == 1 else "blocks"
        print(f"Successfully replaced {count} {noun} in {doc_id}.")
        return 0

    parser.print_help()
    return 0
