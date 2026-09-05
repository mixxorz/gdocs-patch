import argparse
import json
import sys
from collections.abc import Sequence
from importlib.metadata import version
from pathlib import Path
from typing import Any, NoReturn

import httplib2
from google.auth.exceptions import GoogleAuthError
from googleapiclient.errors import HttpError  # pyright: ignore[reportMissingTypeStubs]
from oauthlib.oauth2 import OAuth2Error  # pyright: ignore[reportMissingTypeStubs]

from gsheets_patch.auth import AuthenticationError, load_credentials, login
from gsheets_patch.client import GoogleSheetsClient
from gsheets_patch.errors import api_error_value, error_json, error_value
from gsheets_patch.schema import describe_schema
from gsheets_patch.skill import SKILL


class InputError(Exception):
    """Raised when local command input cannot be read or parsed."""


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(error_json(error_value(message, kind="input")), file=sys.stderr)
        raise SystemExit(2)


def read_json_body(value: str) -> Any:
    try:
        if value == "-":
            text = sys.stdin.read()
        elif value.startswith("@"):
            text = Path(value[1:]).read_text(encoding="utf-8")
        else:
            text = value
        return json.loads(text)
    except (OSError, UnicodeError, ValueError) as error:
        raise InputError(f"Could not read JSON body: {error}") from None


def add_api_arguments(
    parser: argparse.ArgumentParser, native_method: str, *, body: bool = False
) -> None:
    # Store the native route with the parser rather than derive it from CLI spelling.
    parser.set_defaults(operation=native_method)
    parser.add_argument("spreadsheet_id", metavar="SPREADSHEET_ID")
    if body:
        parser.add_argument(
            "--body", required=True, help="Inline JSON, @file, or - for stdin."
        )
    parser.add_argument("--fields")


def build_parser() -> argparse.ArgumentParser:
    parser = JSONArgumentParser(
        prog="gsheets-patch", description="Call selected Google Sheets v4 methods."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('gsheets-patch')}"
    )
    commands = parser.add_subparsers(dest="command")

    # Spreadsheet-level operations live at the root; repeating "spreadsheets"
    # would add no information. Filtered reads put their options in the JSON body.
    get = commands.add_parser("get")
    add_api_arguments(get, "spreadsheets.get")
    get.add_argument(
        "--include-grid-data", action=argparse.BooleanOptionalAction, default=None
    )
    get.add_argument(
        "--exclude-tables-in-banded-ranges",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    get.add_argument("--ranges", action="append")
    add_api_arguments(
        commands.add_parser("get-by-data-filter"),
        "spreadsheets.getByDataFilter",
        body=True,
    )
    add_api_arguments(
        commands.add_parser("batch-update"),
        "spreadsheets.batchUpdate",
        body=True,
    )

    values = commands.add_parser("values").add_subparsers(
        dest="values_command", required=True
    )

    # Values reads share render options. A single read takes a positional range;
    # a batch read accepts repeated --ranges without splitting sheet names on commas.
    value_get = values.add_parser("get")
    add_api_arguments(value_get, "spreadsheets.values.get")
    value_get.add_argument("range", metavar="RANGE")
    batch_get = values.add_parser("batch-get")
    add_api_arguments(batch_get, "spreadsheets.values.batchGet")
    batch_get.add_argument("--ranges", action="append")
    for read_parser in (value_get, batch_get):
        read_parser.add_argument("--major-dimension")
        read_parser.add_argument("--value-render-option")
        read_parser.add_argument("--date-time-render-option")

    # These batch/filter methods carry ranges and operation options in the body,
    # so they need no command-specific query flags.
    body_methods = {
        "batch-get-by-data-filter": "spreadsheets.values.batchGetByDataFilter",
        "batch-update": "spreadsheets.values.batchUpdate",
        "batch-update-by-data-filter": "spreadsheets.values.batchUpdateByDataFilter",
        "batch-clear": "spreadsheets.values.batchClear",
        "batch-clear-by-data-filter": "spreadsheets.values.batchClearByDataFilter",
    }
    for name, native_method in body_methods.items():
        add_api_arguments(values.add_parser(name), native_method, body=True)

    # Single-range writes take their input/response options as query parameters.
    # Append adds an insertion policy; the rest is shared with update.
    update = values.add_parser("update")
    add_api_arguments(update, "spreadsheets.values.update", body=True)
    append = values.add_parser("append")
    add_api_arguments(append, "spreadsheets.values.append", body=True)
    for write_parser in (update, append):
        write_parser.add_argument("range", metavar="RANGE")
        write_parser.add_argument("--value-input-option", required=True)
        write_parser.add_argument(
            "--include-values-in-response",
            action=argparse.BooleanOptionalAction,
            default=None,
        )
        write_parser.add_argument("--response-value-render-option")
        write_parser.add_argument("--response-date-time-render-option")
    append.add_argument("--insert-data-option")

    clear = values.add_parser("clear")
    add_api_arguments(clear, "spreadsheets.values.clear", body=True)
    clear.add_argument("range", metavar="RANGE")

    # Local guidance doesn't need Google credentials. Interactive OAuth login
    # is deliberately CLI-only.
    commands.add_parser("skill", help="Show agent workflows and native API examples.")
    schema = commands.add_parser("schema")
    schema.add_argument("name", nargs="?")
    auth = commands.add_parser("auth").add_subparsers(
        dest="auth_command", required=True
    )
    auth_login = auth.add_parser("login")
    auth_login.add_argument("--client-secrets", type=Path)
    return parser


def report_error(value: dict[str, Any]) -> int:
    print(error_json(value), file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "skill":
        sys.stdout.write(SKILL)
        return 0
    if args.command == "auth":
        try:
            path = login(client_secrets=args.client_secrets)
        except AuthenticationError as error:
            return report_error(error_value(error, kind="auth"))
        except (OAuth2Error, GoogleAuthError, OSError, ValueError):
            return report_error(error_value("Google OAuth login failed.", kind="auth"))
        print(json.dumps({"credentials": str(path)}, indent=2))
        return 0
    if args.command == "schema":
        try:
            result = describe_schema(args.name)
        except KeyError:
            return report_error(
                error_value(f"Unknown schema: {args.name}", kind="input")
            )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command is None:
        parser.print_help()
        return 0

    try:
        client = GoogleSheetsClient(credentials=load_credentials())
        # Parser routing fields aren't API parameters. Leave omitted options out,
        # and decode only the body source; its contents stay native Google JSON.
        routing_fields = {"command", "values_command", "auth_command", "operation"}
        arguments = {
            key: read_json_body(value) if key == "body" else value
            for key, value in vars(args).items()
            if key not in routing_fields and value is not None
        }
        result = client.call(args.operation, **arguments)
    except (InputError, ValueError, TypeError) as error:
        return report_error(error_value(error, kind="input"))
    except (AuthenticationError, GoogleAuthError) as error:
        return report_error(error_value(error, kind="auth"))
    except HttpError as error:
        return report_error(api_error_value(error))
    except (httplib2.HttpLib2Error, OSError) as error:
        return report_error(error_value(error, kind="transport"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
