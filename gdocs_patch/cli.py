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
    describe_syntax,
    edit_document,
    read_document,
    write_document,
)
from gdocs_patch.compiler import UnsupportedTransformation
from gdocs_patch.xhtml import XHTMLParseError


class InputError(Exception):
    """Raised when command input is invalid."""


def _read_json_object() -> dict[str, object]:
    try:
        value = json.load(sys.stdin)
    except (ValueError, UnicodeDecodeError, RecursionError):
        # Hide the decoder's low-level exception if this helper is called directly.
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
    commands.add_parser(
        "read",
        help="Read a Google document as canonical XHTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Input (JSON on stdin):
              {"docId":"DOCUMENT_ID","offset":1,"limit":200}

            docId is required. offset and limit are optional line-based pagination.

            Example:
              printf '%s\\n' '{"docId":"DOCUMENT_ID"}' | gdocs-patch read

            Output: canonical XHTML on stdout.
            """
        ),
    )
    commands.add_parser(
        "write",
        help="Write canonical XHTML to a Google document.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Input (JSON on stdin):
              {"docId":"DOCUMENT_ID","content":"<XHTML>",
               "allowBulletNormalization":false}

            docId and content are required. content is the complete target XHTML.
            allowBulletNormalization is optional and defaults to false. Set it to true
            to allow customized lists to be converted to the closest supported preset.

            Example:
              jq -n --arg docId "DOCUMENT_ID" --rawfile content document.xhtml \\
                '{docId: $docId, content: $content}' | gdocs-patch write

            Output: a plain-text success message.
            """
        ),
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
        "syntax_detail",
        nargs="?",
        choices=("reference",),
        help="Show the detailed reference for a content type.",
    )
    commands.add_parser(
        "edit",
        help="Edit exact text in canonical XHTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Input (JSON on stdin):
              {"docId":"DOCUMENT_ID","edits":[{"oldText":"old","newText":"new"}],
               "allowBulletNormalization":false}

            docId and edits are required. oldText must match exactly once.
            allowBulletNormalization is optional and defaults to false. Set it to true
            to allow customized lists to be converted to the closest supported preset.

            Example:
              printf '%s\\n' \\
                '{"docId":"DOCUMENT_ID","edits":[{"oldText":"old","newText":"new"}]}' \\
                | gdocs-patch edit

            Output: a plain-text success message.
            """
        ),
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

    if args.command == "syntax":
        sys.stdout.write(
            describe_syntax(
                args.syntax_topic,
                reference=args.syntax_detail == "reference",
            )
        )
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
        except (InputError, AuthenticationError, GoogleAuthError, HttpError) as error:
            print(f"gdocs-patch: error: {error}", file=sys.stderr)
            return 1
        sys.stdout.write(output)
        return 0

    if args.command == "write":
        try:
            input_object = _read_json_object()
            unknown_fields = input_object.keys() - {
                "docId",
                "content",
                "allowBulletNormalization",
            }
            if unknown_fields:
                field = sorted(unknown_fields)[0]
                raise InputError(f"Write command input has unknown field: {field}.")

            doc_id = input_object.get("docId")
            if not isinstance(doc_id, str):
                raise InputError("Write command input requires string field: docId.")

            content = input_object.get("content")
            if not isinstance(content, str):
                raise InputError("Write command input requires string field: content.")

            allow_bullet_normalization = input_object.get(
                "allowBulletNormalization", False
            )
            if not isinstance(allow_bullet_normalization, bool):
                raise InputError(
                    "Write command input allowBulletNormalization must be a boolean."
                )

            client = GoogleDocsClient(credentials=load_credentials())
            write_document(
                client=client,
                doc_id=doc_id,
                content=content,
                allow_bullet_normalization=allow_bullet_normalization,
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
        print(f"Successfully wrote to {doc_id}.")
        return 0

    if args.command == "edit":
        try:
            input_object = _read_json_object()
            unknown_fields = input_object.keys() - {
                "docId",
                "edits",
                "allowBulletNormalization",
            }
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

            allow_bullet_normalization = input_object.get(
                "allowBulletNormalization", False
            )
            if not isinstance(allow_bullet_normalization, bool):
                raise InputError(
                    "Edit command input allowBulletNormalization must be a boolean."
                )

            if not edits:
                raise InputError(
                    "Edit command input is invalid. edits must contain at least one "
                    "replacement."
                )
            for edit_index, edit in enumerate(edits):
                if not edit.old_text:
                    raise InputError(
                        f"edits[{edit_index}].oldText must not be empty in {doc_id}."
                    )

            client = GoogleDocsClient(credentials=load_credentials())
            count = edit_document(
                client=client,
                doc_id=doc_id,
                edits=edits,
                allow_bullet_normalization=allow_bullet_normalization,
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
        print(f"Successfully replaced {count} {noun} in {doc_id}.")
        return 0

    parser.print_help()
    return 0
