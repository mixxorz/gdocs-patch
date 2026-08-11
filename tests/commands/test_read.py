from gdocs_patch.commands.read import read_document
from tests.commands.support import FakeGoogleDocsClient


def test_reads_requested_xhtml_lines() -> None:
    client = FakeGoogleDocsClient()

    result = read_document(client=client, doc_id="doc-1", offset=8, limit=4)

    assert result == (
        "            <g:section-style />\n"
        "            <g:paragraph>\n"
        "              <span>Hello world</span>\n"
        "            </g:paragraph>\n"
    )
    assert client.get_document_ids == ["doc-1"]
