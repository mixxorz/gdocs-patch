import re
from typing import Any, cast

import httplib2
from google.auth.credentials import Credentials
from google_auth_httplib2 import (  # pyright: ignore[reportMissingTypeStubs]
    AuthorizedHttp,
)
from googleapiclient.discovery import (  # pyright: ignore[reportMissingTypeStubs]
    build,  # pyright: ignore[reportUnknownVariableType]
)


class GoogleSheetsClient:
    """Thin transport wrapper around Google Sheets v4 methods."""

    def __init__(
        self, *, credentials: Credentials, http: httplib2.Http | None = None
    ) -> None:
        transport = http or httplib2.Http(timeout=60)
        self._service = cast(
            Any,
            build(
                "sheets",
                "v4",
                http=AuthorizedHttp(credentials, http=transport),
                cache_discovery=False,
                static_discovery=True,
            ),
        )

    def call(self, native_method: str, **snake_case_params: Any) -> dict[str, Any]:
        # Discovery resources are factories: spreadsheets.values.get becomes
        # service.spreadsheets().values().get(...).
        resource = self._service
        parts = native_method.split(".")
        for name in parts[:-1]:
            resource = getattr(resource, name)()
        method = getattr(resource, parts[-1])
        # Translate only parameter names, never keys inside the native JSON body.
        # None means an omitted option; false and zero must still reach Google.
        params: dict[str, Any] = {}
        for name, value in snake_case_params.items():
            if value is not None:
                native_name = re.sub(r"_([a-z])", lambda match: match[1].upper(), name)
                params[native_name] = value
        request = method(**params)
        # An ambiguous failure may already have applied an append or structural edit.
        return cast(dict[str, Any], request.execute(num_retries=0))
