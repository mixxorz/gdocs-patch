# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false

from typing import Any, cast

from google.auth.credentials import Credentials
from googleapiclient.discovery import (  # pyright: ignore[reportMissingTypeStubs]
    Resource,
    build,
)


class GoogleDocsClient:
    """Thin transport wrapper around the Google Docs API."""

    def __init__(self, *, credentials: Credentials) -> None:
        self._service = cast(
            Resource,
            build("docs", "v1", credentials=credentials),
        )

    def get_document(self, *, document_id: str) -> dict[str, Any]:
        response = (
            self._service.documents()
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
        response = (
            self._service.documents()
            .batchUpdate(documentId=document_id, body=body)
            .execute()
        )
        return cast(dict[str, Any], response)
