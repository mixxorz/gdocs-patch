import io
import json
from pathlib import Path
from typing import Any

import pytest
from googleapiclient.errors import HttpError
from httplib2 import Response
from oauthlib.oauth2 import AccessDeniedError

from gsheets_patch import cli


class RecordingClient:
    calls: list[tuple[str, dict[str, Any]]] = []
    error: Exception | None = None

    def __init__(self, **_: Any) -> None:
        pass

    def call(self, method: str, **arguments: Any) -> dict[str, Any]:
        self.calls.append((method, arguments))
        if self.error:
            raise self.error
        return {"résultat": 0}


@pytest.fixture(autouse=True)
def offline_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    RecordingClient.calls = []
    RecordingClient.error = None
    monkeypatch.setattr(cli, "GoogleSheetsClient", RecordingClient)
    monkeypatch.setattr(cli, "load_credentials", object)


@pytest.mark.parametrize("source", ["inline", "file", "stdin"])
def test_body_sources(
    source: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = '{"requests":[{"future":{"nil":null,"zero":0}}]}'
    if source == "file":
        path = tmp_path / "body.json"
        path.write_text(body, encoding="utf-8")
        value = f"@{path}"
    elif source == "stdin":
        monkeypatch.setattr("sys.stdin", io.StringIO(body))
        value = "-"
    else:
        value = body

    assert cli.main(["batch-update", "s", "--body", value]) == 0
    assert RecordingClient.calls == [
        (
            "spreadsheets.batchUpdate",
            {
                "spreadsheet_id": "s",
                "body": {"requests": [{"future": {"nil": None, "zero": 0}}]},
            },
        )
    ]
    assert json.loads(capsys.readouterr().out) == {"résultat": 0}


@pytest.mark.parametrize(
    ("argv", "method"),
    [
        (["get-by-data-filter", "s", "--body", "{}"], "spreadsheets.getByDataFilter"),
        (
            ["values", "batch-get-by-data-filter", "s", "--body", "{}"],
            "spreadsheets.values.batchGetByDataFilter",
        ),
        (
            ["values", "batch-clear-by-data-filter", "s", "--body", "{}"],
            "spreadsheets.values.batchClearByDataFilter",
        ),
    ],
)
def test_data_filter_command_spellings(argv: list[str], method: str) -> None:
    assert cli.main(argv) == 0
    assert RecordingClient.calls[0][0] == method


def test_cli_forwards_repeated_ranges_and_false() -> None:
    assert (
        cli.main(
            [
                "get",
                "s",
                "--no-include-grid-data",
                "--exclude-tables-in-banded-ranges",
                "--ranges",
                "A1",
                "--ranges",
                "B2",
            ]
        )
        == 0
    )
    assert RecordingClient.calls[0] == (
        "spreadsheets.get",
        {
            "spreadsheet_id": "s",
            "include_grid_data": False,
            "exclude_tables_in_banded_ranges": True,
            "ranges": ["A1", "B2"],
        },
    )


def test_oauth_denial_is_a_reported_auth_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def denied(**_: Any) -> None:
        raise AccessDeniedError(description="OAuth response details")

    monkeypatch.setattr(cli, "login", denied)
    assert cli.main(["auth", "login"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {"type": "auth", "message": "Google OAuth login failed."}
    }


def test_google_error_is_json_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    RecordingClient.error = HttpError(
        Response({"status": "403"}), b'{"error":{"message":"denied"}}'
    )
    assert cli.main(["get", "s"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {"http_status": 403, "payload": {"error": {"message": "denied"}}}
    }


def test_sdk_argument_error_is_local_input_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    RecordingClient.error = TypeError("SDK rejected argument")
    assert cli.main(["get", "s"]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "error": {"type": "input", "message": "SDK rejected argument"}
    }
