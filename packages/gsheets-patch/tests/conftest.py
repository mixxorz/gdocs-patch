import json
from typing import Any

import httplib2
import pytest
from google.oauth2.credentials import Credentials

from gsheets_patch.client import GoogleSheetsClient


class FakeHttp:
    def __init__(self) -> None:
        self.requests: list[tuple[str, str, bytes | None, dict[str, str]]] = []
        self.responses: list[tuple[int, bytes]] = [(200, b'{"ok":true}')]

    def request(
        self,
        uri: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        **_: Any,
    ) -> tuple[httplib2.Response, bytes]:
        self.requests.append((method, uri, body, headers or {}))
        status, content = self.responses.pop(0)
        return httplib2.Response({"status": str(status)}), content


@pytest.fixture
def fake_http() -> FakeHttp:
    return FakeHttp()


@pytest.fixture
def sheets_client(fake_http: FakeHttp) -> GoogleSheetsClient:
    return GoogleSheetsClient(
        credentials=Credentials(token="offline-token"),
        http=fake_http,  # type: ignore[arg-type]
    )


def json_body(body: bytes | None) -> Any:
    return None if body is None else json.loads(body)
