import json
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from google.oauth2.credentials import Credentials

from gsheets_patch import auth
from gsheets_patch.schema import METHODS, describe_schema


def test_credentials_save_and_load_are_isolated_to_configured_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "config" / "credentials.json"
    monkeypatch.setattr(auth, "DEFAULT_CREDENTIALS_PATH", path)
    credentials = Credentials(
        token="access",
        refresh_token="refresh",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="id",
        client_secret="secret",
        expiry=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    auth.save_credentials(credentials)

    assert path.is_file()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    loaded = auth.load_credentials()
    assert isinstance(loaded, Credentials)
    assert loaded.refresh_token == "refresh"


def test_environment_token_takes_precedence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(auth, "DEFAULT_CREDENTIALS_PATH", tmp_path / "missing.json")
    monkeypatch.setenv(auth.TOKEN_ENVIRONMENT_VARIABLE, "environment-token")
    credentials = auth.load_credentials()
    assert credentials.token == "environment-token"


def test_expired_credentials_refresh_and_are_saved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "credentials.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(auth, "DEFAULT_CREDENTIALS_PATH", path)
    events: list[str] = []

    class ExpiredCredentials:
        expired = True

        def refresh(self, request: Any) -> None:
            events.append(type(request).__name__)

    monkeypatch.setattr(
        auth.Credentials,
        "from_authorized_user_file",
        lambda *args, **kwargs: ExpiredCredentials(),
    )
    monkeypatch.setattr(
        auth, "save_credentials", lambda credentials: events.append("save")
    )
    assert auth.load_credentials().__class__ is ExpiredCredentials
    assert events == ["Request", "save"]


def test_schema_listing_is_limited_to_supported_methods() -> None:
    listing = describe_schema()
    assert listing["methods"] == list(METHODS)
    assert "Request" in listing["schemas"]
    assert "spreadsheets.create" not in listing["methods"]


@pytest.mark.parametrize(
    ("name", "kind", "reference"),
    [
        ("spreadsheets.batchUpdate", "method", "BatchUpdateSpreadsheetRequest"),
        ("RepeatCellRequest", "schema", "GridRange"),
    ],
)
def test_known_schema_lookup_retains_references(
    name: str, kind: str, reference: str
) -> None:
    result = describe_schema(name)
    assert result["kind"] == kind
    assert reference in json.dumps(result["definition"])
