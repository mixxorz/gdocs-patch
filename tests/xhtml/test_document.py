import pytest

from gdocs_patch.models import (
    Body,
    Document,
    DocumentTab,
    NamedStyle,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Segment,
    Tab,
    TextRun,
    TextStyle,
    UrlLink,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def test_document_envelope_round_trip_uses_canonical_xml() -> None:
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


def test_document_tab_projects_body_and_segment_maps() -> None:
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

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Regions">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        '              <span g:bold="true" g:italic="false">Body</span>\n'
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "        <g:headers>\n"
        '          <g:header g:key="header-map-key" '
        'g:segment-id="embedded-header-id">\n'
        "            <g:paragraph>\n"
        "              <span>Header</span>\n"
        "            </g:paragraph>\n"
        "          </g:header>\n"
        "        </g:headers>\n"
        "        <g:footers />\n"
        "        <g:footnotes />\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert deserialize_document(xhtml) == document


def test_named_style_projection_preserves_order() -> None:
    styles = [
        NamedStyle(named_style_type="NAMED_STYLE_TYPE_UNSPECIFIED"),
        NamedStyle(
            named_style_type="NORMAL_TEXT",
            text_style=TextStyle(italic=True, link=UrlLink(url="https://example.test")),
            paragraph_style=ParagraphStyle(
                named_style_type="NORMAL_TEXT", alignment="END"
            ),
        ),
        NamedStyle(named_style_type="HEADING_6"),
    ]
    document = Document(
        document_id="doc-named",
        title="Named",
        tabs=[
            Tab(
                tab_id="ordered",
                title="Ordered",
                index=0,
                children=[],
                content=DocumentTab(named_styles=styles),
            )
        ],
    )

    xhtml = serialize_document(document)
    actual = deserialize_document(xhtml)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-named" '
        'g:title="Named">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="ordered" g:title="Ordered" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:named-styles>\n"
        '          <g:named-style g:type="NAMED_STYLE_TYPE_UNSPECIFIED" />\n'
        '          <g:named-style g:type="NORMAL_TEXT" g:italic="true">\n'
        '            <a href="https://example.test" />\n'
        '            <g:paragraph-style g:named-style-type="NORMAL_TEXT" '
        'g:alignment="END" />\n'
        "          </g:named-style>\n"
        '          <g:named-style g:type="HEADING_6" />\n'
        "        </g:named-styles>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert actual == document


def test_rejects_wrong_xhtml_namespace() -> None:
    with pytest.raises(XHTMLParseError, match="unsupported XHTML namespace"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="urn:wrong" xmlns:g="urn:gdocs-patch:xhtml:1" '
            'g:document-id="doc-1" g:title="Example"><body /></html>'
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
