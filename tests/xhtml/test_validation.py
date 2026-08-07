from collections.abc import Callable

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
from gdocs_patch.xhtml import base as base_module
from gdocs_patch.xhtml import decoder as decoder_module

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
        (DECLARATION + "<html>", "/document"),
        (document()[len(DECLARATION) :], "/document"),
        (
            document().replace(
                'xmlns="http://www.w3.org/1999/xhtml"', 'xmlns="urn:wrong"'
            ),
            "/html",
        ),
        (
            document().replace(
                'xmlns:g="urn:gdocs-patch:xhtml:1"', 'xmlns:g="urn:wrong"'
            ),
            "/html",
        ),
        (document().replace(' g:title="Validation"', ' g:unknown="x"'), "/html"),
        (document().replace("<body>", "<body><aside />"), "/html"),
        (document().replace(' g:index="0"', ' g:index="0" g:unknown="x"'), "/g:tab[1]"),
        (
            document().replace("<g:document-tab>", "<g:document-tab><g:unknown />"),
            "/g:document-tab",
        ),
        (document('<p g:unknown="x" />'), "/section[1]"),
        (document('<p><g:paragraph-style g:unknown="x" /></p>'), "/g:paragraph-style"),
        (document('<table g:unknown="x"><tbody /></table>'), "/section[1]"),
        (
            document('<g:list g:list-id="id" g:unknown="x"><li><p /></li></g:list>'),
            "/section[1]",
        ),
        (document().replace('g:index="0"', 'g:index="bad"'), "/@g:index"),
        (
            document().replace('g:index="0"', 'g:index="0" g:nesting-level="1.5"'),
            "/@g:nesting-level",
        ),
        (document('<p><span g:bold="yes">x</span></p>'), "/@g:bold"),
        (document('<p><span g:font-size="nan">x</span></p>'), "/@g:font-size"),
        (
            document('<p><span g:baseline-offset="HIGH">x</span></p>'),
            "/@g:baseline-offset",
        ),
        (document('<p><span g:foreground-red="1">x</span></p>'), "/*[1]"),
        (document('<p><a href="x" g:tab-id="tab"><span>x</span></a></p>'), "/*[1]"),
        (document('<p><span g:font-size="inf">x</span></p>'), "/*[1]"),
        (document("<p><span><em /></span></p>"), "/*[1]"),
        (document('<p><span><br g:unknown="x" /></span></p>'), "/br"),
        (document("<p>raw<span>x</span></p>"), "/section[1]"),
        (document("<p><span>x</span>raw</p>"), "/section[1]"),
        (
            document('<table><tbody><tr><td rowspan="0" /></tr></tbody></table>'),
            "/@rowspan",
        ),
        (
            document(
                '<table><colgroup><col g:width-type="FIXED_WIDTH" /></colgroup><tbody /></table>'
            ),
            "/col[1]",
        ),
        (
            document(
                '<g:list g:list-id="id" g:bullet-preset="BULLET_CHECKBOX"><li><p /></li></g:list>'
            ),
            "/section[1]",
        ),
        (
            document('<g:list g:bullet-preset="INVALID"><li><p /></li></g:list>'),
            "/@g:bullet-preset",
        ),
        (document().replace("<section><g:section-style /></section>", ""), "/g:body"),
        (document().replace("<g:section-style />", ""), "/section[1]"),
        (document("<section><g:section-style /></section>"), "/section[1]"),
        (
            document("<p><g:paragraph-style /><span>x</span><g:paragraph-style /></p>"),
            "/section[1]",
        ),
        (document("<table><tbody /><colgroup /><tbody /></table>"), "/section[1]"),
        (
            document(
                '<g:list g:list-id="id"><li><g:bullet-style /><p /><g:bullet-style /></li></g:list>'
            ),
            "/li[1]",
        ),
        (
            document(
                '<p><span g:foreground-red="2" g:foreground-green="0" g:foreground-blue="0">x</span></p>'
            ),
            "/*[1]",
        ),
        (document("<p><g:auto-text /></p>"), "/*[1]"),
        (document("<p><time /></p>"), "/*[1]"),
        (document("<p><g:footnote-reference /></p>"), "/*[1]"),
        (document("<p><g:inline-object /></p>"), "/*[1]"),
        (document("<p><g:person /></p>"), "/*[1]"),
        (document("<p><g:rich-link /></p>"), "/*[1]"),
        (document('<p><g:auto-text g:type="INVALID" /></p>'), "/@g:type"),
        (
            document('<p><time g:date-id="d" g:date-format="INVALID" /></p>'),
            "/@g:date-format",
        ),
        (document('<p><g:person g:person-id="id" g:unknown="x" /></p>'), "/*[1]"),
    ],
)
def test_invalid_grammar_is_contextual_xhtml_parse_error(xhtml: str, path: str) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)


@pytest.mark.parametrize("nesting_level", [-1, -99])
def test_rejects_negative_tab_nesting_level(nesting_level: int) -> None:
    xhtml = document().replace(
        'g:index="0"', f'g:index="0" g:nesting-level="{nesting_level}"'
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/g:tab[1]/@g:nesting-level" in str(error.value)
    assert "non-negative" in str(error.value)


@pytest.mark.parametrize(
    ("xhtml", "expected_attribute"),
    [
        (
            document()
            .replace('g:index="0"', 'g:index="invalid"')
            .replace("<g:document-tab>", "<g:document-tab><g:unknown />"),
            "@g:index",
        ),
        (
            document(
                '<p><g:paragraph-style g:keep-with-next="invalid">'
                "<g:unknown /></g:paragraph-style></p>"
            ),
            "@g:keep-with-next",
        ),
        (
            document(
                "",
                metadata='<g:document-style g:page-number-start="invalid">'
                "<g:unknown /></g:document-style>",
            ),
            "@g:page-number-start",
        ),
        (
            document(
                "",
                metadata='<g:named-styles><g:named-style g:type="INVALID">'
                "<g:unknown /></g:named-style></g:named-styles>",
            ),
            "@g:type",
        ),
    ],
)
def test_parent_scalar_error_precedes_invalid_descendant(
    xhtml: str, expected_attribute: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    expected_path = {
        "@g:index": "/g:tab[1]/@g:index",
        "@g:keep-with-next": "/g:paragraph-style/@g:keep-with-next",
        "@g:page-number-start": "/g:document-style/@g:page-number-start",
        "@g:type": "/g:named-style[1]/@g:type",
    }[expected_attribute]
    assert expected_path in str(error.value)
    assert expected_attribute in str(error.value)


@pytest.mark.parametrize(
    ("xhtml", "expected_attribute"),
    [
        (
            document(
                '<g:list g:list-id="id"><li g:nesting-level="invalid">'
                "BAD<p /></li></g:list>"
            ),
            "@g:nesting-level",
        ),
        (
            document(
                '<table><colgroup><col g:width-type="INVALID">'
                "<g:unknown /></col></colgroup><tbody /></table>"
            ),
            "@g:width-type",
        ),
        (
            document(
                "<p><g:positioned-objects><g:positioned-object>"
                "<g:unknown /></g:positioned-object></g:positioned-objects></p>"
            ),
            "g:id",
        ),
        (
            document(
                '<p><g:paragraph-style><g:tab-stops><g:tab-stop g:alignment="INVALID">'
                "<g:unknown /></g:tab-stop></g:tab-stops></g:paragraph-style></p>"
            ),
            "@g:alignment",
        ),
        (
            document("<p><g:auto-text><g:unknown /></g:auto-text></p>"),
            "g:type",
        ),
        (
            document('<p><a href="x" g:tab-id="tab">BAD<span /></a></p>'),
            "link target attribute combination",
        ),
        (
            document(
                '<g:list g:list-id="id"><li><p /></li></g:list>',
                metadata='<g:list-definitions><g:list-definition g:list-id="id">'
                '<g:list-level g:glyph-format="%0" g:glyph-symbol="x">'
                '<a href="x" g:tab-id="tab">BAD</a></g:list-level>'
                "</g:list-definition></g:list-definitions>",
            ),
            "link target attribute combination",
        ),
    ],
    ids=[
        "list-item",
        "table-column",
        "positioned-object",
        "tab-stop",
        "non-text-required",
        "content-link",
        "metadata-link",
    ],
)
def test_local_attribute_error_precedes_text_or_child_error(
    xhtml: str, expected_attribute: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    if expected_attribute == "@g:nesting-level":
        expected_path = "/li[1]/@g:nesting-level"
    elif expected_attribute == "@g:width-type":
        expected_path = "/colgroup/col[1]/@g:width-type"
    elif expected_attribute == "g:id":
        expected_path = "/g:positioned-object[1]"
    elif expected_attribute == "@g:alignment":
        expected_path = "/g:tab-stop[1]/@g:alignment"
    elif expected_attribute == "g:type":
        expected_path = "/section[1]/*[1]/*[1]"
    elif "g:list-definitions" in xhtml:
        expected_path = "/g:list-level[1]/a"
    else:
        expected_path = "/section[1]/*[1]/*[1]"
    assert expected_path in str(error.value)
    assert expected_attribute in str(error.value)


@pytest.mark.parametrize(
    ("xhtml", "path", "message"),
    [
        (
            document(
                '<g:list g:list-id="id" g:bullet-preset="BULLET_CHECKBOX">'
                "<g:unknown /></g:list>"
            ),
            "/section[1]/*[1]",
            "unknown child element g:unknown",
        ),
        (
            document(
                '<table><colgroup><col g:width-type="FIXED_WIDTH">'
                "<g:unknown /></col></colgroup><tbody /></table>"
            ),
            "/colgroup/col[1]",
            "unknown child element g:unknown",
        ),
    ],
    ids=["list-identity", "table-column-width"],
)
def test_child_validation_precedes_cross_field_check(
    xhtml: str, path: str, message: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)
    assert message in str(error.value)


@pytest.mark.parametrize(
    ("xhtml", "path"),
    [
        (
            document(
                "",
                metadata='<g:list-definitions><g:list-definition g:list-id="id">'
                '<g:list-level g:glyph-format="%0" g:glyph-symbol="x" g:bold="true">'
                '<a href="https://example.test"><g:unknown /></a></g:list-level>'
                "</g:list-definition></g:list-definitions>",
            ),
            "/g:list-level[1]/a",
        ),
        (
            document(
                '<p><g:auto-text g:type="PAGE_NUMBER" g:bold="true">'
                "<g:unknown /></g:auto-text></p>"
            ),
            "/section[1]/*[1]/*[1]",
        ),
    ],
    ids=["metadata-text-style", "non-text-owning-model"],
)
def test_child_validation_precedes_text_style_construction(
    monkeypatch: pytest.MonkeyPatch, xhtml: str, path: str
) -> None:
    class RejectingTextStyle:
        def __init__(self, **_kwargs: object) -> None:
            raise ValueError("TextStyle constructed too early")

    monkeypatch.setattr(base_module, "TextStyle", RejectingTextStyle)

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)
    assert "unknown child element g:unknown" in str(error.value)


def test_malformed_xml_preserves_element_tree_cause() -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(DECLARATION + "<html>")

    assert error.value.__cause__ is not None


def test_model_constructor_error_preserves_cause_and_nearest_path() -> None:
    xhtml = document(
        '<p><span g:foreground-red="2" g:foreground-green="0" '
        'g:foreground-blue="0">x</span></p>'
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/*[1]" in str(error.value)
    assert isinstance(error.value.__cause__, ValueError)


def test_structured_color_constructor_error_preserves_cause() -> None:
    xhtml = document(
        '<p><g:paragraph-style><g:shading-color g:red="0" g:green="2" '
        'g:blue="0" /></g:paragraph-style></p>'
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/g:shading-color" in str(error.value)
    assert isinstance(error.value.__cause__, ValueError)


@pytest.mark.parametrize(
    ("model_name", "xhtml", "path"),
    [
        (
            "ListLevel",
            document(
                "",
                metadata='<g:list-definitions><g:list-definition g:list-id="id">'
                '<g:list-level g:glyph-format="%0" g:glyph-symbol="x" />'
                "</g:list-definition></g:list-definitions>",
            ),
            "/g:list-level[1]",
        ),
        (
            "TableColumn",
            document(
                '<table><colgroup><col g:width-type="EVENLY_DISTRIBUTED" />'
                "</colgroup><tbody /></table>"
            ),
            "/col[1]",
        ),
        (
            "TableCellStyle",
            document(
                '<table><tbody><tr><td rowspan="2"><g:cell-style />'
                "</td></tr></tbody></table>"
            ),
            "/td[1]",
        ),
    ],
)
def test_invariant_model_constructor_error_is_contextual_and_preserves_cause(
    monkeypatch: pytest.MonkeyPatch, model_name: str, xhtml: str, path: str
) -> None:
    def reject_construction(**_kwargs: object) -> object:
        raise ValueError("model invariant failed")

    replacement: Callable[..., object] = reject_construction
    monkeypatch.setattr(decoder_module, model_name, replacement)

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)
    assert "model invariant failed" in str(error.value)
    assert isinstance(error.value.__cause__, ValueError)


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
