import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    Color,
    Dimension,
    Document,
    DocumentStyle,
    DocumentTab,
    NamedStyle,
    Paragraph,
    ParagraphBorder,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Segment,
    Tab,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
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


def _pt(magnitude: float) -> Dimension:
    return Dimension(magnitude=magnitude, unit="PT")


def test_round_trips_complete_document_style_and_preserves_empty_presence() -> None:
    complete = DocumentStyle(
        background_color=Color(red=0.1, green=0.2, blue=0.3),
        document_mode="PAGES",
        page_width=_pt(612),
        page_height=_pt(792),
        margin_top=_pt(1),
        margin_bottom=_pt(2),
        margin_left=_pt(3),
        margin_right=_pt(4),
        margin_header=_pt(5),
        margin_footer=_pt(6),
        default_header_id="header-default",
        default_footer_id="footer-default",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_even_page_header_footer=True,
        use_first_page_header_footer=False,
        use_custom_header_footer_margins=True,
        flip_page_orientation=False,
        page_number_start=7,
    )
    document = Document(
        document_id="doc-style",
        title="Style",
        tabs=[
            Tab(
                tab_id="complete",
                title="Complete",
                index=0,
                children=[],
                content=DocumentTab(document_style=complete),
            ),
            Tab(
                tab_id="empty",
                title="Empty",
                index=1,
                children=[],
                content=DocumentTab(document_style=DocumentStyle()),
            ),
            Tab(
                tab_id="unset",
                title="Unset",
                index=2,
                children=[],
                content=DocumentTab(),
            ),
        ],
    )

    xhtml = serialize_document(document)
    actual = deserialize_document(xhtml)

    assert actual == document
    assert xhtml.count("<g:document-style") == 2
    complete_style = actual.tabs[0].content.document_style
    assert isinstance(complete_style, DocumentStyle)
    for name in (
        "page_width",
        "page_height",
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "margin_header",
        "margin_footer",
    ):
        dimension = getattr(complete_style, name)
        assert isinstance(dimension, Dimension)
        assert dimension.unit == "PT"
    assert actual.tabs[1].content.document_style == DocumentStyle()
    assert actual.tabs[2].content.document_style is UNSET


def test_round_trips_ordered_complete_named_styles_and_empty_presence() -> None:
    border = ParagraphBorder(
        color=None, width=_pt(1), padding=_pt(2), dash_style="DASH"
    )
    complete_text = TextStyle(
        bold=True,
        italic=False,
        underline=True,
        strikethrough=False,
        small_caps=True,
        baseline_offset="SUBSCRIPT",
        font_size=_pt(11),
        font_family="Arial",
        font_weight=600,
        foreground_color=Color(red=0.1, green=0.2, blue=0.3),
        background_color=None,
        link=UrlLink(url="https://example.test"),
    )
    complete_paragraph = ParagraphStyle(
        named_style_type="NORMAL_TEXT",
        alignment="JUSTIFIED",
        direction="RIGHT_TO_LEFT",
        line_spacing=120,
        spacing_mode="COLLAPSE_LISTS",
        space_above=_pt(1),
        space_below=_pt(2),
        indent_first_line=_pt(3),
        indent_start=_pt(4),
        indent_end=_pt(5),
        keep_lines_together=True,
        keep_with_next=False,
        avoid_widow_and_orphan=True,
        page_break_before=False,
        heading_id="heading",
        border_between=border,
        border_top=border,
        border_bottom=border,
        border_left=border,
        border_right=border,
        shading_color=Color(red=0.4, green=0.5, blue=0.6),
        tab_stops=[TabStop(offset=_pt(36), alignment="CENTER")],
    )
    types = ["NAMED_STYLE_TYPE_UNSPECIFIED", "NORMAL_TEXT", "HEADING_6"]
    styles = [NamedStyle(named_style_type=value) for value in types]
    styles[1] = NamedStyle(
        named_style_type="NORMAL_TEXT",
        text_style=complete_text,
        paragraph_style=complete_paragraph,
    )
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
            ),
            Tab(
                tab_id="empty",
                title="Empty",
                index=1,
                children=[],
                content=DocumentTab(named_styles=[]),
            ),
            Tab(
                tab_id="unset",
                title="Unset",
                index=2,
                children=[],
                content=DocumentTab(),
            ),
        ],
    )

    xhtml = serialize_document(document)
    actual = deserialize_document(xhtml)

    assert actual == document
    ordered = actual.tabs[0].content.named_styles
    assert isinstance(ordered, list)
    assert [style.named_style_type for style in ordered] == types
    assert "<a" in xhtml
    assert '<g:named-style g:type="NORMAL_TEXT"' in xhtml
    assert '<g:paragraph-style g:named-style-type="NORMAL_TEXT"' in xhtml
    assert actual.tabs[1].content.named_styles == []
    assert actual.tabs[2].content.named_styles is UNSET


def test_decodes_named_style_metadata_in_any_order() -> None:
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Named">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        "<g:document-tab><g:named-styles><g:named-style "
        'g:type="NORMAL_TEXT" g:bold="true">'
        '<g:paragraph-style g:named-style-type="NORMAL_TEXT" />'
        '<a href="https://example.test" />'
        "</g:named-style></g:named-styles></g:document-tab>"
        "</g:tab></body></html>"
    )

    actual = deserialize_document(xhtml)
    content = actual.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert content.named_styles == [
        NamedStyle(
            named_style_type="NORMAL_TEXT",
            text_style=TextStyle(bold=True, link=UrlLink(url="https://example.test")),
            paragraph_style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
        )
    ]
    canonical = serialize_document(actual)
    assert '<g:named-style g:type="NORMAL_TEXT"' in canonical
    assert '<g:paragraph-style g:named-style-type="NORMAL_TEXT"' in canonical


def test_deserializes_attributes_in_noncanonical_order() -> None:
    source = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html g:title="Title" xmlns:g="urn:gdocs-patch:xhtml:1" '
        'g:document-id="doc" xmlns="http://www.w3.org/1999/xhtml">'
        '<body><g:tab g:index="0" g:title="Tab" g:tab-id="tab">'
        "<g:document-tab /></g:tab></body></html>"
    )

    document = deserialize_document(source)

    assert document.document_id == "doc"
    assert document.tabs[0].tab_id == "tab"


def test_rejects_outer_named_style_named_style_type_attribute() -> None:
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Named">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        "<g:document-tab><g:named-styles><g:named-style "
        'g:named-style-type="NORMAL_TEXT" />'
        "</g:named-styles></g:document-tab></g:tab></body></html>"
    )

    with pytest.raises(
        XHTMLParseError,
        match=r"g:named-style\[1\].*unknown attribute g:named-style-type",
    ):
        deserialize_document(xhtml)


def test_rejects_nested_child_in_empty_section_style() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/html/body/g:tab\[1\].*/g:section-style: unknown child element g:unknown",
    ):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Style">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section>"
            "<g:section-style><g:unknown /></g:section-style>"
            "</section></g:body></g:document-tab>"
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


def test_rejects_duplicate_required_body_wrapper() -> None:
    with pytest.raises(XHTMLParseError, match="at most one body"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" '
            'g:document-id="doc-1" g:title="Example">'
            "<body /><body />"
            "</html>"
        )
