import pytest

from gdocs_patch.models import Document, Tab
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def test_serializes_and_deserializes_document_and_tab_envelope() -> None:
    document = Document(
        document_id="doc-1",
        title="Example & Report",
        revision_id="revision-1",
        suggestions_view_mode="SUGGESTIONS_INLINE",
        tabs=[
            Tab(
                tab_id="tab-root",
                title="Root",
                index=0,
                nesting_level=0,
                icon_emoji="📄",
                children=[
                    Tab(
                        tab_id="tab-child",
                        title="Child",
                        index=1,
                        nesting_level=1,
                        parent_tab_id="tab-root",
                        children=[],
                    )
                ],
            )
        ],
    )

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Example &amp; Report" g:revision-id="revision-1" '
        'g:suggestions-view-mode="SUGGESTIONS_INLINE">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-root" g:title="Root" g:index="0" '
        'g:icon-emoji="📄">\n'
        "      <g:child-tabs>\n"
        '        <g:tab g:tab-id="tab-child" g:title="Child" g:index="1" '
        'g:nesting-level="1" g:parent-tab-id="tab-root" />\n'
        "      </g:child-tabs>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert deserialize_document(xhtml) == document


def test_rejects_malformed_xml() -> None:
    with pytest.raises(XHTMLParseError, match="XML"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n<html><body></html>'
        )


def test_rejects_wrong_gdocs_namespace() -> None:
    with pytest.raises(XHTMLParseError, match="namespace"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:wrong" g:document-id="doc-1" g:title="Example">'
            "<body />"
            "</html>"
        )


def test_rejects_duplicate_body() -> None:
    with pytest.raises(XHTMLParseError, match="body"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" '
            'g:document-id="doc-1" g:title="Example">'
            "<body /><body />"
            "</html>"
        )
