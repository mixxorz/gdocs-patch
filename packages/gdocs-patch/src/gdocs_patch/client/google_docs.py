from typing import Any, cast

from google.auth.credentials import Credentials
from googleapiclient.discovery import (  # pyright: ignore[reportMissingTypeStubs]
    Resource,
    build,  # pyright: ignore[reportUnknownVariableType]
)


class GoogleDocsClient:
    """Thin transport wrapper around the Google Docs API."""

    def __init__(self, *, credentials: Credentials) -> None:
        self._service = cast(
            Resource,
            build("docs", "v1", credentials=credentials),
        )

    def get_document(self, *, document_id: str) -> dict[str, Any]:
        response = (  # pyright: ignore[reportUnknownVariableType]
            self._service.documents()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            .get(documentId=document_id, includeTabsContent=True)
            .execute()
        )
        return cast(dict[str, Any], response)

    def batch_update(
        self,
        *,
        document_id: str,
        body: dict[str, object],
    ) -> dict[str, Any]:
        response = (  # pyright: ignore[reportUnknownVariableType]
            self._service.documents()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType]
            .batchUpdate(documentId=document_id, body=body)
            .execute()
        )
        return cast(dict[str, Any], response)
