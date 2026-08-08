import pytest

from gdocs_patch.models import (
    UNSET,
    AutoText,
    Body,
    BookmarkLink,
    Color,
    ColumnBreak,
    DateElement,
    Dimension,
    Document,
    DocumentTab,
    Equation,
    FootnoteReference,
    HorizontalRule,
    InlineObjectReference,
    PageBreak,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
    PersonReference,
    RichLink,
    SectionBreak,
    SectionStyle,
    Tab,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def document_with_runs(*runs: ParagraphElement) -> Document:
    return Document(
        document_id="doc-1",
        title="Paragraph",
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
                                elements=list(runs),
                            ),
                        ]
                    )
                ),
            )
        ],
    )


def paragraph_from(document: Document) -> Paragraph:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)
    return paragraph


@pytest.mark.parametrize(
    ("paragraph_element", "expected_tag"),
    [
        (
            AutoText(
                auto_text_type="PAGE_NUMBER",
                text_style=TextStyle(bold=True),
            ),
            "g:auto-text",
        ),
        (ColumnBreak(text_style=TextStyle(italic=False)), "g:column-break"),
        (
            DateElement(
                date_id="date-1",
                date_format="DATE_FORMAT_ISO8601",
                display_text="",
                locale="en-US",
                time_format="TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
                time_zone_id="UTC",
                timestamp="2026-08-08T12:00:00Z",
                text_style=TextStyle(underline=True),
            ),
            "time",
        ),
        (Equation(), "g:equation"),
        (
            FootnoteReference(
                footnote_id="footnote-1",
                footnote_number="3",
                text_style=TextStyle(strikethrough=False),
            ),
            "g:footnote-reference",
        ),
        (HorizontalRule(text_style=TextStyle(small_caps=True)), "hr"),
        (
            InlineObjectReference(
                inline_object_id="object-1",
                text_style=TextStyle(baseline_offset="SUBSCRIPT"),
            ),
            "g:inline-object",
        ),
        (PageBreak(text_style=TextStyle(font_family="Arial")), "g:page-break"),
        (
            PersonReference(
                person_id="person-1",
                email="",
                name="",
                text_style=TextStyle(font_weight=700),
            ),
            "g:person",
        ),
        (
            RichLink(
                rich_link_id="rich-link-1",
                uri="https://smart-chip.example/document",
                title="",
                mime_type="",
                text_style=TextStyle(
                    link=UrlLink(url="https://outer-link.example/target")
                ),
            ),
            "g:rich-link",
        ),
    ],
    ids=lambda value: (
        type(value).__name__ if isinstance(value, ParagraphElement) else str(value)
    ),
)
def test_round_trips_non_text_paragraph_element(
    paragraph_element: ParagraphElement, expected_tag: str
) -> None:
    document = document_with_runs(paragraph_element)

    xhtml = serialize_document(document)

    assert f"<{expected_tag}" in xhtml
    if isinstance(paragraph_element, RichLink):
        assert 'href="https://outer-link.example/target"' in xhtml
        assert 'g:uri="https://smart-chip.example/document"' in xhtml
    assert paragraph_from(deserialize_document(xhtml)).elements == [paragraph_element]


def test_styled_auto_text_uses_canonical_attribute_order() -> None:
    xhtml = serialize_document(
        document_with_runs(
            AutoText(
                auto_text_type="PAGE_NUMBER",
                text_style=TextStyle(bold=True, font_family="Arial"),
            )
        )
    )

    assert (
        '<g:auto-text g:type="PAGE_NUMBER" g:bold="true" g:font-family="Arial" />'
        in xhtml
    )


def test_styled_date_element_uses_canonical_attribute_order() -> None:
    xhtml = serialize_document(
        document_with_runs(
            DateElement(
                date_id="date-1",
                date_format="DATE_FORMAT_ISO8601",
                display_text="2026-08-08",
                locale="en-US",
                time_format="TIME_FORMAT_HOUR_MINUTE",
                time_zone_id="UTC",
                timestamp="2026-08-08T12:00:00Z",
                text_style=TextStyle(bold=True, font_family="Arial"),
            )
        )
    )

    assert (
        '<time g:date-id="date-1" g:date-format="DATE_FORMAT_ISO8601" '
        'g:time-format="TIME_FORMAT_HOUR_MINUTE" g:display-text="2026-08-08" '
        'g:locale="en-US" g:time-zone-id="UTC" datetime="2026-08-08T12:00:00Z" '
        'g:bold="true" g:font-family="Arial" />'
    ) in xhtml


def test_rejects_multiple_children_in_content_link() -> None:
    xhtml = serialize_document(
        document_with_runs(
            TextRun(
                content="linked",
                text_style=TextStyle(link=UrlLink(url="https://example.com")),
            )
        )
    )
    xhtml = xhtml.replace("</a>", "<g:page-break /></a>", 1)

    with pytest.raises(XHTMLParseError, match="exactly one"):
        deserialize_document(xhtml)


def test_round_trips_complete_paragraph_metadata() -> None:
    opaque_border = ParagraphBorder(
        color=Color(red=0.1, green=0.2, blue=0.3),
        width=Dimension(magnitude=1),
        padding=Dimension(magnitude=2),
        dash_style="SOLID",
    )
    transparent_border = ParagraphBorder(
        color=None,
        width=Dimension(magnitude=3),
        padding=Dimension(magnitude=4),
        dash_style="DASH",
    )
    style = ParagraphStyle(
        named_style_type="HEADING_2",
        alignment="CENTER",
        direction="RIGHT_TO_LEFT",
        line_spacing=120,
        spacing_mode="NEVER_COLLAPSE",
        space_above=Dimension(magnitude=6),
        space_below=Dimension(magnitude=8),
        indent_first_line=Dimension(magnitude=18),
        indent_start=Dimension(magnitude=36),
        indent_end=Dimension(magnitude=12),
        keep_lines_together=True,
        keep_with_next=False,
        avoid_widow_and_orphan=True,
        page_break_before=False,
        heading_id="heading-2",
        border_between=opaque_border,
        border_top=transparent_border,
        border_bottom=opaque_border,
        border_left=transparent_border,
        border_right=opaque_border,
        shading_color=None,
        tab_stops=[
            TabStop(offset=Dimension(magnitude=36), alignment="START"),
            TabStop(offset=Dimension(magnitude=72), alignment="END"),
        ],
    )
    document = document_with_runs(TextRun(content="First"), TextRun(content="Second"))
    paragraph = paragraph_from(document)
    paragraph.style = style
    paragraph.positioned_object_ids = ["object-1", "object-2"]

    xhtml = serialize_document(document)

    assert "<h2>" in xhtml
    assert "g:named-style-type=" not in xhtml
    for fragment in (
        'g:space-above="6"',
        'g:space-below="8"',
        'g:indent-first-line="18"',
        'g:indent-start="36"',
        'g:indent-end="12"',
        '<g:border-between g:dash-style="SOLID" g:width="1" g:padding="2">',
        '<g:color g:red="0.1" g:green="0.2" g:blue="0.3" />',
        '<g:border-top g:dash-style="DASH" g:width="3" g:padding="4">',
        '<g:color g:transparent="true" />',
        '<g:shading-color g:transparent="true" />',
        '<g:tab-stop g:alignment="START" g:offset="36" />',
        '<g:tab-stop g:alignment="END" g:offset="72" />',
        '<g:positioned-object g:id="object-1" />',
        '<g:positioned-object g:id="object-2" />',
    ):
        assert fragment in xhtml

    expected = style
    expected.space_above = Dimension(magnitude=6, unit="PT")
    expected.space_below = Dimension(magnitude=8, unit="PT")
    expected.indent_first_line = Dimension(magnitude=18, unit="PT")
    expected.indent_start = Dimension(magnitude=36, unit="PT")
    expected.indent_end = Dimension(magnitude=12, unit="PT")
    for border in (
        expected.border_between,
        expected.border_top,
        expected.border_bottom,
        expected.border_left,
        expected.border_right,
    ):
        assert isinstance(border, ParagraphBorder)
        border.width = Dimension(magnitude=border.width.magnitude, unit="PT")
        border.padding = Dimension(magnitude=border.padding.magnitude, unit="PT")
    assert isinstance(expected.tab_stops, list)
    for tab_stop in expected.tab_stops:
        tab_stop.offset = Dimension(magnitude=tab_stop.offset.magnitude, unit="PT")
    decoded_paragraph = paragraph_from(deserialize_document(xhtml))
    assert decoded_paragraph.style == expected
    assert decoded_paragraph.positioned_object_ids == ["object-1", "object-2"]
    assert decoded_paragraph.elements == [
        TextRun(content="First"),
        TextRun(content="Second"),
    ]

    moved = xhtml
    # Move both metadata blocks between the two spans; metadata position is permissive.
    start = moved.index("<g:paragraph-style")
    style_end = moved.index("</g:paragraph-style>", start) + len("</g:paragraph-style>")
    style_xml = moved[start:style_end]
    moved = moved[:start] + moved[style_end:]
    start = moved.index("<g:positioned-objects")
    objects_end = moved.index("</g:positioned-objects>", start) + len(
        "</g:positioned-objects>"
    )
    objects_xml = moved[start:objects_end]
    moved = moved[:start] + moved[objects_end:]
    insertion = moved.index("</span>", moved.index("<h2>")) + len("</span>")
    moved = moved[:insertion] + style_xml + objects_xml + moved[insertion:]
    assert paragraph_from(deserialize_document(moved)).elements == [
        TextRun(content="First"),
        TextRun(content="Second"),
    ]


@pytest.mark.parametrize(
    ("named_style_type", "tag"),
    [
        (UNSET, "g:paragraph"),
        ("NAMED_STYLE_TYPE_UNSPECIFIED", "g:named-style-unspecified"),
        ("NORMAL_TEXT", "p"),
        ("TITLE", "g:title"),
        ("SUBTITLE", "g:subtitle"),
        ("HEADING_1", "h1"),
        ("HEADING_2", "h2"),
        ("HEADING_3", "h3"),
        ("HEADING_4", "h4"),
        ("HEADING_5", "h5"),
        ("HEADING_6", "h6"),
    ],
)
def test_paragraph_named_style_uses_canonical_tag(
    named_style_type: object, tag: str
) -> None:
    document = document_with_runs(TextRun(content="Tagged"))
    paragraph = paragraph_from(document)
    paragraph.style = (
        UNSET
        if named_style_type is UNSET
        else ParagraphStyle(named_style_type=named_style_type)  # type: ignore[arg-type]
    )

    xhtml = serialize_document(document)

    assert f"<{tag}>" in xhtml
    assert paragraph_from(deserialize_document(xhtml)).style == paragraph.style


def test_preserves_empty_paragraph_metadata_collections() -> None:
    document = document_with_runs(TextRun(content="Empty"))
    paragraph = paragraph_from(document)
    paragraph.style = ParagraphStyle(tab_stops=[])
    paragraph.positioned_object_ids = []

    xhtml = serialize_document(document)

    assert "<g:tab-stops />" in xhtml
    assert "<g:positioned-objects />" in xhtml
    decoded = paragraph_from(deserialize_document(xhtml))
    assert isinstance(decoded.style, ParagraphStyle)
    assert decoded.style.tab_stops == []
    assert decoded.positioned_object_ids == []


def test_round_trips_text_style_link_colors_and_newlines() -> None:
    run = TextRun(
        content="First\nSecond\n",
        text_style=TextStyle(
            bold=True,
            italic=False,
            underline=True,
            strikethrough=False,
            small_caps=True,
            baseline_offset="SUPERSCRIPT",
            font_size=Dimension(magnitude=12, unit="UNIT_UNSPECIFIED"),
            font_family="Arial",
            font_weight=700,
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )

    xhtml = serialize_document(document_with_runs(run))

    assert '<a g:bookmark-id="bookmark-1" g:tab-id="tab-1">' in xhtml
    assert (
        '<span g:bold="true" g:italic="false" g:underline="true" '
        'g:strikethrough="false" g:small-caps="true" '
        'g:baseline-offset="SUPERSCRIPT" g:font-size="12" '
        'g:font-family="Arial" g:font-weight="700" '
        'g:foreground-red="0.1" g:foreground-green="0.2" '
        'g:foreground-blue="0.3" g:background-color="transparent">'
        "First<br />Second<br /></span>"
    ) in xhtml
    assert xhtml.count("<br />") == 2

    decoded = deserialize_document(xhtml)
    content = decoded.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)
    decoded_run = paragraph.elements[0]
    assert decoded_run == TextRun(
        content="First\nSecond\n",
        text_style=TextStyle(
            bold=True,
            italic=False,
            underline=True,
            strikethrough=False,
            small_caps=True,
            baseline_offset="SUPERSCRIPT",
            font_size=Dimension(magnitude=12, unit="PT"),
            font_family="Arial",
            font_weight=700,
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )


def test_round_trips_carriage_returns_with_canonical_character_references() -> None:
    run = TextRun(content="before\rmiddle\r\nafter")

    xhtml = serialize_document(document_with_runs(run))

    assert "<span>before&#13;middle&#13;<br />after</span>" in xhtml
    assert paragraph_from(deserialize_document(xhtml)).elements == [run]


def test_round_trips_precision_sensitive_text_style_number() -> None:
    magnitude = 0.12345678901234567
    document = document_with_runs(
        TextRun(
            content="Precise",
            text_style=TextStyle(
                font_size=Dimension(magnitude=magnitude),
                foreground_color=Color(red=magnitude),
            ),
        )
    )

    xhtml = serialize_document(document)

    assert f'g:font-size="{magnitude!r}"' in xhtml
    assert f'g:foreground-red="{magnitude!r}"' in xhtml
    decoded = deserialize_document(xhtml)
    content = decoded.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)
    run = paragraph.elements[0]
    assert isinstance(run, TextRun)
    assert isinstance(run.text_style, TextStyle)
    assert run.text_style.font_size == Dimension(magnitude=magnitude, unit="PT")
    assert run.text_style.foreground_color == Color(red=magnitude)


def test_point_integer_is_canonical_after_decode_and_reencode() -> None:
    xhtml = serialize_document(
        document_with_runs(
            TextRun(
                content="Integer",
                text_style=TextStyle(font_size=Dimension(magnitude=12.0)),
            )
        )
    )

    assert 'g:font-size="12"' in xhtml
    assert serialize_document(deserialize_document(xhtml)) == xhtml


def test_decodes_literal_line_feed_breaks_and_preserves_run_boundaries() -> None:
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Runs">'
        "<body>"
        '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style />"
        "<p><span>Literal\nBreak<br />Tail</span><span /><span>Adjacent</span></p>"
        "</section></g:body></g:document-tab>"
        "</g:tab>"
        "</body></html>"
    )

    document = deserialize_document(xhtml)
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)

    assert paragraph.elements == [
        TextRun(content="Literal\nBreak\nTail"),
        TextRun(content=""),
        TextRun(content="Adjacent"),
    ]


def test_rejects_named_style_type_metadata_on_gdocs_paragraph() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/g:paragraph-style: named style type is owned by the paragraph element",
    ):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Style">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section><g:section-style />"
            '<g:paragraph><g:paragraph-style g:named-style-type="NORMAL_TEXT" />'
            "</g:paragraph></section></g:body></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )


def test_rejects_out_of_range_structured_color_with_parse_context() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/g:paragraph-style/g:shading-color: .*red.*between 0.* and 1",
    ):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Color">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section><g:section-style /><p>"
            '<g:paragraph-style><g:shading-color g:red="2" g:green="0" g:blue="0" />'
            "</g:paragraph-style></p></section></g:body></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )


def test_rejects_text_between_child_elements() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/html/body/g:tab\[1\].*text is not permitted under this parent",
    ):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Tail">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section><g:section-style /><p>"
            "<g:paragraph-style />BAD<span>ok</span>"
            "</p></section></g:body></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )


@pytest.mark.parametrize(
    "attributes",
    [
        'href="https://example.com" g:tab-id="tab-1"',
        'g:bookmark-id="bookmark-1" g:heading-id="heading-1"',
        "",
    ],
)
def test_rejects_invalid_link_target_combinations(attributes: str) -> None:
    with pytest.raises(XHTMLParseError, match="link target"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Links">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section><g:section-style /><p>"
            f"<a {attributes}><span>Text</span></a>"
            "</p></section></g:body></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )
