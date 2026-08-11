from typing import Any

SOURCE_RESPONSE: dict[str, Any] = {
    "documentId": "doc-1",
    "title": "Example",
    "revisionId": "rev-1",
    "tabs": [
        {
            "tabProperties": {"tabId": "tab-1", "title": "Main", "index": 0},
            "documentTab": {
                "body": {
                    "content": [
                        {
                            "startIndex": 1,
                            "endIndex": 1,
                            "sectionBreak": {"sectionStyle": {}},
                        },
                        {
                            "startIndex": 1,
                            "endIndex": 13,
                            "paragraph": {
                                "elements": [
                                    {
                                        "startIndex": 1,
                                        "endIndex": 13,
                                        "textRun": {
                                            "content": "Hello world\n",
                                            "textStyle": {},
                                        },
                                    }
                                ],
                                "paragraphStyle": {},
                            },
                        },
                    ]
                }
            },
        }
    ],
}


class FakeGoogleDocsClient:
    def __init__(self) -> None:
        self.get_document_ids: list[str] = []
        self.batch_bodies: list[dict[str, object]] = []

    def get_document(self, *, document_id: str) -> dict[str, Any]:
        self.get_document_ids.append(document_id)
        return SOURCE_RESPONSE

    def batch_update(
        self, *, document_id: str, body: dict[str, object]
    ) -> dict[str, Any]:
        self.batch_bodies.append(body)
        return {}
