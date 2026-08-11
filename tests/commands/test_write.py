from gdocs_patch.commands.write import write_document
from tests.commands.support import FakeGoogleDocsClient


def test_writes_compiled_xhtml_to_requested_document() -> None:
    client = FakeGoogleDocsClient()
    content = """<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="different-doc" g:title="Different title" g:revision-id="different-revision">
  <body>
    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">
      <g:document-tab>
        <g:body>
          <section>
            <g:section-style />
            <g:paragraph>
              <span>Hello </span><span>brave </span><span>world</span>
            </g:paragraph>
          </section>
        </g:body>
      </g:document-tab>
    </g:tab>
  </body>
</html>
"""

    write_document(client=client, doc_id="doc-1", content=content)

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
