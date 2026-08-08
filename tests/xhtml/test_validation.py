import pytest

from gdocs_patch.models import (
    Body,
    Bullet,
    Document,
    DocumentTab,
    NamedStyle,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Tab,
    Table,
    TableCell,
    TableCellStyle,
    TableColumn,
    TableRow,
    TextRun,
    TextStyle,
    UrlLink,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document

DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def document(structure: str = "", *, metadata: str = "") -> str:
    return (
        DECLARATION + '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Validation">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        f"<g:document-tab>{metadata}<g:body><section><g:section-style />"
        f"{structure}</section></g:body></g:document-tab>"
        "</g:tab></body></html>"
    )


@pytest.mark.parametrize(
    ("xhtml", "path"),
    [
        (document()[len(DECLARATION) :], "/document"),
        (
            document().replace(
                'xmlns="http://www.w3.org/1999/xhtml"', 'xmlns="urn:wrong"'
            ),
            "/html",
        ),
        (document().replace(' g:title="Validation"', ' g:unknown="x"'), "/html"),
        (document().replace(' g:index="0"', ' g:index="0" g:unknown="x"'), "/g:tab[1]"),
        (document('<p g:unknown="x" />'), "/section[1]"),
        (document('<p><g:paragraph-style g:unknown="x" /></p>'), "/g:paragraph-style"),
        (document('<p><span g:bold="yes">x</span></p>'), "/@g:bold"),
        (
            document('<p><span g:baseline-offset="HIGH">x</span></p>'),
            "/@g:baseline-offset",
        ),
        (document('<p><span><br g:unknown="x" /></span></p>'), "/br"),
        (document().replace("<g:section-style />", ""), "/section[1]"),
        (document("<p><g:auto-text /></p>"), "/g:auto-text[1]"),
    ],
)
def test_invalid_grammar_is_contextual_xhtml_parse_error(xhtml: str, path: str) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)


def test_rejects_empty_body() -> None:
    xhtml = document().replace(
        "<g:body><section><g:section-style /></section></g:body>", "<g:body />"
    )

    with pytest.raises(
        XHTMLParseError, match=r"g:body: expected at least one child element"
    ):
        deserialize_document(xhtml)


@pytest.mark.parametrize(
    "attributes",
    ["", 'href="https://example.test" g:bookmark-id="bookmark"'],
)
def test_anchor_target_validation_precedes_malformed_content(attributes: str) -> None:
    xhtml = document(f"<p><a {attributes}>raw<g:unknown /></a></p>")

    with pytest.raises(
        XHTMLParseError, match="invalid link target attribute combination"
    ):
        deserialize_document(xhtml)


def test_rejects_negative_tab_nesting_level() -> None:
    nesting_level = -1
    xhtml = document().replace(
        'g:index="0"', f'g:index="0" g:nesting-level="{nesting_level}"'
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/g:tab[1]/@g:nesting-level" in str(error.value)
    assert "non-negative" in str(error.value)


def test_malformed_xml_preserves_element_tree_cause() -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(DECLARATION + "<html>")

    assert error.value.__cause__ is not None


def test_decodes_all_unique_metadata_in_any_order_without_reordering_content() -> None:
    xhtml = (
        DECLARATION + '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Order">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        "<g:child-tabs /><g:document-tab>"
        "<g:body><section><p><span>first</span>"
        '<g:positioned-objects><g:positioned-object g:id="object" /></g:positioned-objects>'
        '<g:paragraph-style g:alignment="CENTER" /><span>second</span></p>'
        '<g:list g:list-id="list"><li><p><span>item</span></p>'
        '<g:bullet-style g:bold="true"><a href="https://example.test" /></g:bullet-style>'
        "</li></g:list><table><tbody><tr><td><p><span>cell-one</span></p>"
        '<g:cell-style g:content-alignment="BOTTOM" /><p><span>cell-two</span></p>'
        '</td></tr></tbody><colgroup><col g:width-type="EVENLY_DISTRIBUTED" />'
        "</colgroup></table><g:section-style /></section></g:body>"
        '<g:named-styles><g:named-style g:type="NORMAL_TEXT" g:italic="true">'
        '<g:paragraph-style g:alignment="END" /><a href="https://named.test" />'
        "</g:named-style></g:named-styles></g:document-tab>"
        "</g:tab></body></html>"
    )
    expected = Document(
        document_id="doc",
        title="Order",
        tabs=[
            Tab(
                tab_id="tab",
                title="Tab",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                elements=[
                                    TextRun(content="first"),
                                    TextRun(content="second"),
                                ],
                                style=ParagraphStyle(
                                    named_style_type="NORMAL_TEXT", alignment="CENTER"
                                ),
                                positioned_object_ids=["object"],
                            ),
                            Paragraph(
                                elements=[TextRun(content="item")],
                                style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
                                bullet=Bullet(
                                    list_id="list",
                                    text_style=TextStyle(
                                        bold=True,
                                        link=UrlLink(url="https://example.test"),
                                    ),
                                ),
                            ),
                            Table(
                                column_styles=[
                                    TableColumn(width_type="EVENLY_DISTRIBUTED")
                                ],
                                rows=[
                                    TableRow(
                                        cells=[
                                            TableCell(
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="cell-one")
                                                        ],
                                                        style=ParagraphStyle(
                                                            named_style_type="NORMAL_TEXT"
                                                        ),
                                                    ),
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="cell-two")
                                                        ],
                                                        style=ParagraphStyle(
                                                            named_style_type="NORMAL_TEXT"
                                                        ),
                                                    ),
                                                ],
                                                style=TableCellStyle(
                                                    content_alignment="BOTTOM"
                                                ),
                                            )
                                        ]
                                    )
                                ],
                            ),
                        ]
                    ),
                    named_styles=[
                        NamedStyle(
                            named_style_type="NORMAL_TEXT",
                            text_style=TextStyle(
                                italic=True,
                                link=UrlLink(url="https://named.test"),
                            ),
                            paragraph_style=ParagraphStyle(alignment="END"),
                        )
                    ],
                ),
            )
        ],
    )
    assert deserialize_document(xhtml) == expected
