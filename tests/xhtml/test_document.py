import pytest

from gdocs_patch.models import (
    Body,
    Document,
    DocumentTab,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Segment,
    Tab,
    TextRun,
    TextStyle,
)
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


def test_round_trips_document_tab_body_and_segment_regions() -> None:
    document = Document(
        document_id="doc-1",
        title="Regions",
        tabs=[
            Tab(
                tab_id="tab-1",
                title="Main",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
                                elements=[
                                    TextRun(
                                        content="Body\n",
                                        text_style=TextStyle(bold=True, italic=False),
                                    )
                                ],
                            ),
                        ]
                    ),
                    headers={
                        "header-map-key": Segment(
                            segment_id="embedded-header-id",
                            content=[Paragraph(elements=[TextRun(content="Header\n")])],
                        )
                    },
                    footers={},
                    footnotes={},
                ),
            )
        ],
    )

    xhtml = serialize_document(document)

    assert "<g:document-tab>" in xhtml
    assert "<g:body>\n          <section>\n            <g:section-style />" in xhtml
    assert (
        '<p>\n              <span g:bold="true" g:italic="false">Body<br /></span>'
        in xhtml
    )
    assert (
        '<g:header g:key="header-map-key" g:segment-id="embedded-header-id">' in xhtml
    )
    assert "<g:footers />" in xhtml
    assert "<g:footnotes />" in xhtml
    assert deserialize_document(xhtml) == document


def test_decodes_document_tab_and_section_metadata_in_any_order() -> None:
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Order">'
        "<body>"
        '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
        "<g:child-tabs />"
        "<g:document-tab>"
        "<g:footnotes />"
        "<g:body><section>"
        "<p><span>First</span><span>Second</span></p>"
        "<g:section-style />"
        "</section></g:body>"
        "<g:headers />"
        "<g:footers />"
        "</g:document-tab>"
        "</g:tab>"
        "</body></html>"
    )
    expected = Document(
        document_id="doc-1",
        title="Order",
        tabs=[
            Tab(
                tab_id="tab-1",
                title="Main",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
                                elements=[
                                    TextRun(content="First"),
                                    TextRun(content="Second"),
                                ],
                            ),
                        ]
                    ),
                    headers={},
                    footers={},
                    footnotes={},
                ),
            )
        ],
    )

    assert deserialize_document(xhtml) == expected


def test_rejects_duplicate_document_tab_region() -> None:
    with pytest.raises(XHTMLParseError, match="g:headers"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Duplicate">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:headers /><g:headers /></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )


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
