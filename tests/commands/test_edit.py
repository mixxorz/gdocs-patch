import re

import pytest

from gdocs_patch.commands.edit import (
    XhtmlEdit,
    XhtmlEditError,
    apply_xhtml_edits,
    edit_document,
)
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


def test_applies_disjoint_edits_against_original_xhtml() -> None:
    assert (
        apply_xhtml_edits(
            xhtml="alpha beta gamma",
            edits=[
                XhtmlEdit(old_text="gamma", new_text="G"),
                XhtmlEdit(old_text="alpha", new_text="A"),
            ],
            document_id="doc-1",
        )
        == "A beta G"
    )


@pytest.mark.parametrize(
    ("xhtml", "edits", "message"),
    [
        (
            "Hello world",
            [XhtmlEdit(old_text="missing", new_text="replacement")],
            "Could not find the exact text for edits[0] in doc-1. The old text "
            "must match exactly including all whitespace and newlines.",
        ),
        (
            "aaaa",
            [XhtmlEdit(old_text="aa", new_text="replacement")],
            "Found 3 occurrences of the text for edits[0] in doc-1. The text "
            "must be unique. Please provide more context to make it unique.",
        ),
        (
            "Hello world",
            [
                XhtmlEdit(old_text="Hello world", new_text="replacement"),
                XhtmlEdit(old_text="world", new_text="replacement"),
            ],
            "edits[0] and edits[1] overlap in doc-1. Merge them into one edit "
            "or target disjoint regions.",
        ),
        (
            "Hello world",
            [XhtmlEdit(old_text="world", new_text="world")],
            "No changes made to doc-1. The replacements produced identical content.",
        ),
    ],
)
def test_rejects_unsafe_exact_edits(
    xhtml: str, edits: list[XhtmlEdit], message: str
) -> None:
    with pytest.raises(XhtmlEditError, match=f"^{re.escape(message)}$"):
        apply_xhtml_edits(xhtml=xhtml, edits=edits, document_id="doc-1")
