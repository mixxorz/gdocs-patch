import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    BookmarkLink,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
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
    elements = list(runs)
    if elements and isinstance(elements[-1], TextRun):
        if not elements[-1].content.endswith("\n"):
            elements[-1].content += "\n"
    else:
        elements.append(TextRun(content="\n"))

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
                                elements=elements,
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


def test_rich_link_distinguishes_chip_uri_from_outer_text_link() -> None:
    rich_link = RichLink(
        rich_link_id="rich-link-1",
        uri="https://smart-chip.example/document",
        title="",
        mime_type="",
        text_style=TextStyle(link=UrlLink(url="https://outer-link.example/target")),
    )

    xhtml = serialize_document(document_with_runs(rich_link))

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        '              <a href="https://outer-link.example/target">\n'
        '                <g:rich-link g:rich-link-id="rich-link-1" '
        'g:uri="https://smart-chip.example/document" g:title="" '
        'g:mime-type="" />\n'
        "              </a>\n"
        "              <span />\n"
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert paragraph_from(deserialize_document(xhtml)).elements == [
        rich_link,
        TextRun(content="\n"),
    ]


def test_content_link_requires_one_paragraph_element() -> None:
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


def test_paragraph_metadata_projects_styles_and_positioned_objects() -> None:
    opaque_border = ParagraphBorder(
        color=Color(red=0.1, green=0.2, blue=0.3),
        width=Dimension(magnitude=1, unit="PT"),
        padding=Dimension(magnitude=2, unit="PT"),
        dash_style="SOLID",
    )
    transparent_border = ParagraphBorder(
        color=None,
        width=Dimension(magnitude=3, unit="PT"),
        padding=Dimension(magnitude=4, unit="PT"),
        dash_style="DASH",
    )
    style = ParagraphStyle(
        named_style_type="HEADING_2",
        alignment="CENTER",
        keep_with_next=False,
        border_left=opaque_border,
        border_right=transparent_border,
        shading_color=None,
        tab_stops=[
            TabStop(offset=Dimension(magnitude=36, unit="PT"), alignment="START")
        ],
    )
    document = document_with_runs(TextRun(content="First"), TextRun(content="Second"))
    paragraph = paragraph_from(document)
    paragraph.style = style
    paragraph.positioned_object_ids = ["object-1", "object-2"]

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <h2>\n"
        '              <g:paragraph-style g:alignment="CENTER" '
        'g:keep-with-next="false">\n'
        '                <g:border-left g:dash-style="SOLID" g:width="1" '
        'g:padding="2">\n'
        '                  <g:color g:red="0.1" g:green="0.2" '
        'g:blue="0.3" />\n'
        "                </g:border-left>\n"
        '                <g:border-right g:dash-style="DASH" g:width="3" '
        'g:padding="4">\n'
        '                  <g:color g:transparent="true" />\n'
        "                </g:border-right>\n"
        '                <g:shading-color g:transparent="true" />\n'
        "                <g:tab-stops>\n"
        '                  <g:tab-stop g:alignment="START" g:offset="36" />\n'
        "                </g:tab-stops>\n"
        "              </g:paragraph-style>\n"
        "              <g:positioned-objects>\n"
        '                <g:positioned-object g:id="object-1" />\n'
        '                <g:positioned-object g:id="object-2" />\n'
        "              </g:positioned-objects>\n"
        "              <span>First</span>\n"
        "              <span>Second</span>\n"
        "            </h2>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )

    decoded_paragraph = paragraph_from(deserialize_document(xhtml))
    assert decoded_paragraph.style == style
    assert decoded_paragraph.positioned_object_ids == ["object-1", "object-2"]
    assert decoded_paragraph.elements == [
        TextRun(content="First"),
        TextRun(content="Second\n"),
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


def test_paragraph_terminal_newline_is_implicit() -> None:
    document = document_with_runs(TextRun(content="First\nSecond\n"))

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        "              <span>First<br />Second</span>\n"
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert deserialize_document(xhtml) == document


def test_text_control_characters_use_canonical_xml_forms() -> None:
    document = document_with_runs(TextRun(content="Before\vMiddle\fAfter\rEnd\nTail\n"))

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        "              <span>Before<g:vertical-tab />Middle<g:form-feed />"
        "After&#13;End<br />Tail</span>\n"
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    assert deserialize_document(xhtml) == document


def test_text_style_projection_normalizes_point_units() -> None:
    run = TextRun(
        content="First\nSecond\n",
        text_style=TextStyle(
            font_size=Dimension(magnitude=12, unit="UNIT_UNSPECIFIED"),
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )

    xhtml = serialize_document(document_with_runs(run))

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        '              <a g:bookmark-id="bookmark-1" g:tab-id="tab-1">\n'
        '                <span g:font-size="12" g:foreground-red="0.1" '
        'g:foreground-green="0.2" g:foreground-blue="0.3" '
        'g:background-color="transparent">First<br />Second</span>\n'
        "              </a>\n"
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )

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
            font_size=Dimension(magnitude=12, unit="PT"),
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )


def test_float_projection_preserves_round_trip_precision() -> None:
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

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Paragraph">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "            <p>\n"
        '              <span g:font-size="0.12345678901234566" '
        'g:foreground-red="0.12345678901234566" g:foreground-green="0" '
        'g:foreground-blue="0">Precise</span>\n'
        "            </p>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
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


def test_text_decode_preserves_literal_line_feeds_and_run_boundaries() -> None:
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
        TextRun(content="Adjacent\n"),
    ]


def test_paragraph_style_metadata_is_owned_by_semantic_tag() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/g:paragraph-style .*: named style type is owned by the paragraph element",
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


def test_structured_color_rejects_out_of_range_components() -> None:
    with pytest.raises(
        XHTMLParseError,
        match=r"/g:paragraph-style/g:shading-color .*: .*red.*between 0.* and 1",
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


@pytest.mark.parametrize(
    "attributes",
    [
        'href="https://example.com" g:tab-id="tab-1"',
        'g:bookmark-id="bookmark-1" g:heading-id="heading-1"',
        "",
    ],
)
def test_link_target_attribute_combinations(attributes: str) -> None:
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
