from typing import Any

import pytest
from googleapiclient.errors import HttpError

from gsheets_patch import client
from gsheets_patch.client import GoogleSheetsClient
from gsheets_patch.errors import api_error_value

from .conftest import FakeHttp, json_body

ROUTES = [
    (
        "spreadsheets.get",
        {
            "spreadsheet_id": "sheet id",
            "include_grid_data": False,
            "ranges": ["'Café 📊'!A1", "B2"],
            "fields": "properties",
        },
        "GET",
        "https://sheets.googleapis.com/v4/spreadsheets/sheet%20id?includeGridData=false&ranges=%27Caf%C3%A9+%F0%9F%93%8A%27%21A1&ranges=B2&fields=properties&alt=json",
        None,
    ),
    (
        "spreadsheets.getByDataFilter",
        {
            "spreadsheet_id": "s",
            "body": {"dataFilters": [{"a1Range": "A:A"}], "unknown": {"value": None}},
        },
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s:getByDataFilter?alt=json",
        {"dataFilters": [{"a1Range": "A:A"}], "unknown": {"value": None}},
    ),
    (
        "spreadsheets.batchUpdate",
        {
            "spreadsheet_id": "s",
            "body": {"requests": [{"futureRequest": {"zero": 0, "nil": None}}]},
        },
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s:batchUpdate?alt=json",
        {"requests": [{"futureRequest": {"zero": 0, "nil": None}}]},
    ),
    (
        "spreadsheets.values.get",
        {"spreadsheet_id": "s", "range": "'Q 1'!A/1", "major_dimension": "ROWS"},
        "GET",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values/%27Q%201%27%21A%2F1?majorDimension=ROWS&alt=json",
        None,
    ),
    (
        "spreadsheets.values.batchGet",
        {
            "spreadsheet_id": "s",
            "ranges": ["A1", "C3"],
            "value_render_option": "FORMULA",
        },
        "GET",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchGet?ranges=A1&ranges=C3&valueRenderOption=FORMULA&alt=json",
        None,
    ),
    (
        "spreadsheets.values.batchGetByDataFilter",
        {"spreadsheet_id": "s", "body": {"dataFilters": []}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchGetByDataFilter?alt=json",
        {"dataFilters": []},
    ),
    (
        "spreadsheets.values.update",
        {
            "spreadsheet_id": "s",
            "range": "A1",
            "value_input_option": "RAW",
            "include_values_in_response": False,
            "body": {"values": [[0, None]]},
        },
        "PUT",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values/A1?valueInputOption=RAW&includeValuesInResponse=false&alt=json",
        {"values": [[0, None]]},
    ),
    (
        "spreadsheets.values.batchUpdate",
        {"spreadsheet_id": "s", "body": {"valueInputOption": "RAW", "data": []}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchUpdate?alt=json",
        {"valueInputOption": "RAW", "data": []},
    ),
    (
        "spreadsheets.values.batchUpdateByDataFilter",
        {"spreadsheet_id": "s", "body": {"valueInputOption": "RAW", "data": []}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchUpdateByDataFilter?alt=json",
        {"valueInputOption": "RAW", "data": []},
    ),
    (
        "spreadsheets.values.append",
        {
            "spreadsheet_id": "s",
            "range": "A1",
            "value_input_option": "USER_ENTERED",
            "insert_data_option": "INSERT_ROWS",
            "body": {"values": [["x"]]},
        },
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values/A1:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS&alt=json",
        {"values": [["x"]]},
    ),
    (
        "spreadsheets.values.clear",
        {"spreadsheet_id": "s", "range": "A1", "body": {}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values/A1:clear?alt=json",
        {},
    ),
    (
        "spreadsheets.values.batchClear",
        {"spreadsheet_id": "s", "body": {"ranges": ["A1"]}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchClear?alt=json",
        {"ranges": ["A1"]},
    ),
    (
        "spreadsheets.values.batchClearByDataFilter",
        {"spreadsheet_id": "s", "body": {"dataFilters": []}},
        "POST",
        "https://sheets.googleapis.com/v4/spreadsheets/s/values:batchClearByDataFilter?alt=json",
        {"dataFilters": []},
    ),
]


@pytest.mark.parametrize(
    ("native_method", "arguments", "method", "url", "body"), ROUTES
)
def test_native_routes(
    sheets_client: GoogleSheetsClient,
    fake_http: FakeHttp,
    native_method: str,
    arguments: dict[str, Any],
    method: str,
    url: str,
    body: Any,
) -> None:
    assert sheets_client.call(native_method, **arguments) == {"ok": True}
    actual_method, actual_url, actual_body, headers = fake_http.requests[0]
    assert (actual_method, actual_url, json_body(actual_body)) == (method, url, body)
    assert headers["authorization"] == "Bearer offline-token"


def test_omitted_options_are_not_sent(
    sheets_client: GoogleSheetsClient, fake_http: FakeHttp
) -> None:
    sheets_client.call("spreadsheets.get", spreadsheet_id="s", ranges=None)
    assert (
        fake_http.requests[0][1]
        == "https://sheets.googleapis.com/v4/spreadsheets/s?alt=json"
    )


def test_google_json_error_is_preserved(
    sheets_client: GoogleSheetsClient, fake_http: FakeHttp
) -> None:
    fake_http.responses = [(400, b'{"error":{"message":"bad range","code":400}}')]
    with pytest.raises(HttpError) as caught:
        sheets_client.call("spreadsheets.values.get", spreadsheet_id="s", range="bad")
    assert api_error_value(caught.value) == {
        "error": {
            "http_status": 400,
            "payload": {"error": {"message": "bad range", "code": 400}},
        }
    }


def test_default_transport_uses_sixty_second_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeouts: list[int] = []
    transport = object()
    monkeypatch.setattr(
        client.httplib2,
        "Http",
        lambda *, timeout: timeouts.append(timeout) or transport,
    )
    monkeypatch.setattr(client, "AuthorizedHttp", lambda credentials, http: http)
    monkeypatch.setattr(client, "build", lambda *args, **kwargs: object())

    GoogleSheetsClient(credentials=object())  # type: ignore[arg-type]
    assert timeouts == [60]


def test_write_503_is_not_retried(
    sheets_client: GoogleSheetsClient, fake_http: FakeHttp
) -> None:
    fake_http.responses = [(503, b"unavailable"), (200, b"{}")]
    with pytest.raises(HttpError):
        sheets_client.call(
            "spreadsheets.values.clear", spreadsheet_id="s", range="A1", body={}
        )
    assert len(fake_http.requests) == 1
