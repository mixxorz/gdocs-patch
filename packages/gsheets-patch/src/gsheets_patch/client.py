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
        resource = self._service
        parts = native_method.split(".")
        for name in parts[:-1]:
            resource = getattr(resource, name)()
        method = getattr(resource, parts[-1])
        params = {
            _camel_case(name): value
            for name, value in snake_case_params.items()
            if value is not None
        }
        request = method(**params)
        return cast(dict[str, Any], request.execute(num_retries=0))


def _camel_case(name: str) -> str:
    return re.sub(r"_([a-z])", lambda match: match[1].upper(), name)
