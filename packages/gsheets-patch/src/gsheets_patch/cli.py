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


class InputError(Exception):
    """Raised when local command input cannot be read or parsed."""


class JSONArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(error_json(error_value(message, kind="input")), file=sys.stderr)
        raise SystemExit(2)


def _body(value: str) -> Any:
    try:
        text = (
            sys.stdin.read()
            if value == "-"
            else Path(value[1:]).read_text(encoding="utf-8")
            if value.startswith("@")
            else value
        )
        return json.loads(text)
    except (OSError, UnicodeError, ValueError) as error:
        raise InputError(f"Could not read JSON body: {error}") from None


def _common(
    parser: argparse.ArgumentParser, native_method: str, *, body: bool = False
) -> None:
    parser.set_defaults(operation=native_method)
    parser.add_argument("spreadsheet_id", metavar="SPREADSHEET_ID")
    if body:
        parser.add_argument(
            "--body", required=True, help="Inline JSON, @file, or - for stdin."
        )
    parser.add_argument("--fields")


def _render_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--major-dimension")
    parser.add_argument("--value-render-option")
    parser.add_argument("--date-time-render-option")


def _response_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--include-values-in-response",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--response-value-render-option")
    parser.add_argument("--response-date-time-render-option")


def build_parser() -> argparse.ArgumentParser:
    parser = JSONArgumentParser(
        prog="gsheets-patch", description="Call selected Google Sheets v4 methods."
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('gsheets-patch')}"
    )
    commands = parser.add_subparsers(dest="command")

    get = commands.add_parser("get")
    _common(get, "spreadsheets.get")
    for flag in ("--include-grid-data", "--exclude-tables-in-banded-ranges"):
        get.add_argument(flag, action=argparse.BooleanOptionalAction, default=None)
    get.add_argument("--ranges", action="append")
    _common(
        commands.add_parser("get-by-data-filter"),
        "spreadsheets.getByDataFilter",
        body=True,
    )
    _common(
        commands.add_parser("batch-update"),
        "spreadsheets.batchUpdate",
        body=True,
    )

    values = commands.add_parser("values").add_subparsers(
        dest="values_command", required=True
    )
    value_get = values.add_parser("get")
    _common(value_get, "spreadsheets.values.get")
    value_get.add_argument("range", metavar="RANGE")
    _render_options(value_get)

    batch_get = values.add_parser("batch-get")
    _common(batch_get, "spreadsheets.values.batchGet")
    batch_get.add_argument("--ranges", action="append")
    _render_options(batch_get)

    body_methods = {
        "batch-get-by-data-filter": "spreadsheets.values.batchGetByDataFilter",
        "batch-update": "spreadsheets.values.batchUpdate",
        "batch-update-by-data-filter": ("spreadsheets.values.batchUpdateByDataFilter"),
        "batch-clear": "spreadsheets.values.batchClear",
        "batch-clear-by-data-filter": "spreadsheets.values.batchClearByDataFilter",
    }
    for name, native_method in body_methods.items():
        _common(values.add_parser(name), native_method, body=True)

    update = values.add_parser("update")
    _common(update, "spreadsheets.values.update", body=True)
    update.add_argument("range", metavar="RANGE")
    update.add_argument("--value-input-option", required=True)
    _response_options(update)

    append = values.add_parser("append")
    _common(append, "spreadsheets.values.append", body=True)
    append.add_argument("range", metavar="RANGE")
    append.add_argument("--value-input-option", required=True)
    append.add_argument("--insert-data-option")
    _response_options(append)

    clear = values.add_parser("clear")
    _common(clear, "spreadsheets.values.clear", body=True)
    clear.add_argument("range", metavar="RANGE")

    schema = commands.add_parser("schema")
    schema.add_argument("name", nargs="?")
    auth = commands.add_parser("auth").add_subparsers(
        dest="auth_command", required=True
    )
    auth_login = auth.add_parser("login")
    auth_login.add_argument("--client-secrets", type=Path)
    return parser


def _arguments(args: argparse.Namespace) -> dict[str, Any]:
    ignored = {"command", "values_command", "auth_command", "operation"}
    return {
        key: _body(value) if key == "body" else value
        for key, value in vars(args).items()
        if key not in ignored and value is not None
    }


def _fail(value: dict[str, Any]) -> int:
    print(error_json(value), file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "auth":
        try:
            path = login(client_secrets=args.client_secrets)
        except AuthenticationError as error:
            return _fail(error_value(error, kind="auth"))
        except (OAuth2Error, GoogleAuthError, OSError, ValueError):
            return _fail(error_value("Google OAuth login failed.", kind="auth"))
        print(json.dumps({"credentials": str(path)}, indent=2))
        return 0
    if args.command == "schema":
        try:
            result = describe_schema(args.name)
        except KeyError:
            return _fail(error_value(f"Unknown schema: {args.name}", kind="input"))
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    if args.command is None:
        parser.print_help()
        return 0
    try:
        result = GoogleSheetsClient(credentials=load_credentials()).call(
            args.operation, **_arguments(args)
        )
    except (InputError, ValueError, TypeError) as error:
        return _fail(error_value(error, kind="input"))
    except (AuthenticationError, GoogleAuthError) as error:
        return _fail(error_value(error, kind="auth"))
    except HttpError as error:
        return _fail(api_error_value(error))
    except (httplib2.HttpLib2Error, OSError) as error:
        return _fail(error_value(error, kind="transport"))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0
