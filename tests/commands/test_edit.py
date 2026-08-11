from gdocs_patch.commands.edit import XhtmlEdit, edit_document
from tests.commands.support import FakeGoogleDocsClient


def test_edits_canonical_xhtml_and_updates_google_document() -> None:
    client = FakeGoogleDocsClient()

    result = edit_document(
        client=client,
        doc_id="doc-1",
        edits=[XhtmlEdit(old_text="world", new_text="brave world")],
    )

    assert result == 1
    assert client.get_document_ids == ["doc-1"]
    assert client.batch_document_ids == ["doc-1"]
    assert client.batch_bodies == [
        {
            "requests": [
                {
                    "insertText": {
                        "location": {"index": 7, "tabId": "tab-1"},
                        "text": "brave ",
                    }
                },
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": 7,
                            "endIndex": 13,
                            "tabId": "tab-1",
                        },
                        "textStyle": {},
                        "fields": (
                            "bold,italic,underline,strikethrough,smallCaps,"
                            "baselineOffset,fontSize,weightedFontFamily,"
                            "foregroundColor,backgroundColor,link"
                        ),
                    }
                },
            ],
            "writeControl": {"requiredRevisionId": "rev-1"},
        }
    ]
