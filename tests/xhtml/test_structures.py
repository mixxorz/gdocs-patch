from typing import cast

import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    BookmarkLink,
    Bullet,
    BulletPreset,
    Color,
    Dimension,
    Document,
    DocumentTab,
    ListDefinition,
    ListLevel,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionColumn,
    SectionStyle,
    Tab,
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableOfContents,
    TableRow,
    TextRun,
    TextStyle,
    UrlLink,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def document_with_section(style: SectionStyle) -> Document:
    return Document(
        document_id="doc-1",
        title="Sections",
        tabs=[
            Tab(
                tab_id="tab-1",
                title="Main",
                index=0,
                children=[],
                content=DocumentTab(body=Body(content=[SectionBreak(style=style)])),
            )
        ],
    )


def decoded_section_style(document: Document) -> SectionStyle:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    section = content.body.content[0]
    assert isinstance(section, SectionBreak)
    return section.style


def test_round_trips_recursive_table_of_contents_in_body() -> None:
    table_of_contents = TableOfContents(
        content=[
            Paragraph(elements=[TextRun(content="First heading")]),
            Paragraph(elements=[TextRun(content="Second heading")]),
            TableOfContents(content=[]),
        ]
    )
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(table_of_contents)

    xhtml = serialize_document(document)

    assert xhtml.count("<g:table-of-contents") == 2
    assert "<g:table-of-contents />" in xhtml
    decoded_content = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded_content, DocumentTab)
    assert isinstance(decoded_content.body, Body)
    assert decoded_content.body.content[1] == table_of_contents


@pytest.mark.parametrize(
    "children",
    [
        "<g:unknown /><section><g:section-style /></section>",
        "<section><g:section-style /></section><g:unknown />",
    ],
)
def test_toc_prioritizes_forbidden_section_over_unknown_siblings(
    children: str,
) -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(TableOfContents(content=[]))
    xhtml = serialize_document(document).replace(
        "<g:table-of-contents />",
        f"<g:table-of-contents>{children}</g:table-of-contents>",
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert str(error.value).endswith("section elements are only valid in a body")


def test_toc_raw_text_precedes_forbidden_section() -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(TableOfContents(content=[]))
    xhtml = serialize_document(document).replace(
        "<g:table-of-contents />",
        "<g:table-of-contents>raw<section><g:section-style /></section>"
        "</g:table-of-contents>",
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert str(error.value).endswith("unexpected text content")


def test_round_trips_complete_section_style() -> None:
    style = SectionStyle(
        columns=[
            SectionColumn(
                width=Dimension(magnitude=234),
                padding_end=Dimension(magnitude=18),
            ),
            SectionColumn(
                width=Dimension(magnitude=240),
                padding_end=Dimension(magnitude=20),
            ),
        ],
        column_separator_style="BETWEEN_EACH_COLUMN",
        content_direction="LEFT_TO_RIGHT",
        section_type="NEXT_PAGE",
        default_header_id="header-default",
        default_footer_id="footer-default",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_first_page_header_footer=True,
        flip_page_orientation=False,
        page_number_start=3,
        margin_top=Dimension(magnitude=72),
        margin_bottom=Dimension(magnitude=73),
        margin_left=Dimension(magnitude=74),
        margin_right=Dimension(magnitude=75),
        margin_header=Dimension(magnitude=36),
        margin_footer=Dimension(magnitude=37),
    )

    xhtml = serialize_document(document_with_section(style))

    for fragment in (
        'g:column-separator-style="BETWEEN_EACH_COLUMN"',
        'g:content-direction="LEFT_TO_RIGHT"',
        'g:section-type="NEXT_PAGE"',
        'g:default-header-id="header-default"',
        'g:default-footer-id="footer-default"',
        'g:even-page-header-id="header-even"',
        'g:even-page-footer-id="footer-even"',
        'g:first-page-header-id="header-first"',
        'g:first-page-footer-id="footer-first"',
        'g:use-first-page-header-footer="true"',
        'g:flip-page-orientation="false"',
        'g:page-number-start="3"',
        'g:margin-top="72"',
        'g:margin-bottom="73"',
        'g:margin-left="74"',
        'g:margin-right="75"',
        'g:margin-header="36"',
        'g:margin-footer="37"',
        '<g:column g:width="234" g:padding-end="18" />',
        '<g:column g:width="240" g:padding-end="20" />',
    ):
        assert fragment in xhtml
    assert xhtml.index('g:width="234"') < xhtml.index('g:width="240"')

    decoded = decoded_section_style(deserialize_document(xhtml))
    assert decoded.column_separator_style == "BETWEEN_EACH_COLUMN"
    assert decoded.content_direction == "LEFT_TO_RIGHT"
    assert decoded.section_type == "NEXT_PAGE"
    assert decoded.default_header_id == "header-default"
    assert decoded.default_footer_id == "footer-default"
    assert decoded.even_page_header_id == "header-even"
    assert decoded.even_page_footer_id == "footer-even"
    assert decoded.first_page_header_id == "header-first"
    assert decoded.first_page_footer_id == "footer-first"
    assert decoded.use_first_page_header_footer is True
    assert decoded.flip_page_orientation is False
    assert decoded.page_number_start == 3
    assert isinstance(decoded.columns, list)
    assert decoded.columns == [
        SectionColumn(
            width=Dimension(magnitude=234, unit="PT"),
            padding_end=Dimension(magnitude=18, unit="PT"),
        ),
        SectionColumn(
            width=Dimension(magnitude=240, unit="PT"),
            padding_end=Dimension(magnitude=20, unit="PT"),
        ),
    ]
    for field in (
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "margin_header",
        "margin_footer",
    ):
        value = getattr(decoded, field)
        assert isinstance(value, Dimension)
        assert value.unit == "PT"


@pytest.mark.parametrize(("columns", "fragment"), [(UNSET, ""), ([], "<g:columns />")])
def test_preserves_unset_versus_empty_section_columns(
    columns: object, fragment: str
) -> None:
    style = SectionStyle(columns=columns)  # type: ignore[arg-type]

    xhtml = serialize_document(document_with_section(style))

    assert ("<g:columns" in xhtml) is bool(fragment)
    assert decoded_section_style(deserialize_document(xhtml)).columns == columns


@pytest.mark.parametrize("missing", ["g:width", "g:padding-end"])
def test_rejects_section_column_missing_required_dimension(missing: str) -> None:
    attributes = 'g:width="100" g:padding-end="10"'.replace(
        f'{missing}="{100 if missing == "g:width" else 10}"', ""
    )
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Bad">'
        '<body><g:tab g:tab-id="tab" g:title="Main" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style><g:columns>"
        f"<g:column {attributes} />"
        "</g:columns></g:section-style></section></g:body></g:document-tab>"
        "</g:tab></body></html>"
    )

    with pytest.raises(XHTMLParseError, match="missing required attribute"):
        deserialize_document(xhtml)


def test_groups_adjacent_existing_and_preset_list_paragraphs() -> None:
    paragraphs = [
        Paragraph(
            elements=[TextRun(content="existing zero")],
            bullet=Bullet(
                list_id="list-1",
                text_style=TextStyle(
                    bold=True, link=UrlLink(url="https://example.com/bullet")
                ),
            ),
        ),
        Paragraph(
            elements=[TextRun(content="existing two")],
            bullet=Bullet(
                list_id="list-1",
                nesting_level=2,
                text_style=TextStyle(italic=True),
            ),
        ),
        Paragraph(elements=[TextRun(content="break")]),
        Paragraph(
            elements=[TextRun(content="preset zero")],
            bullet=BulletPreset(preset="BULLET_DISC_CIRCLE_SQUARE"),
        ),
        Paragraph(
            elements=[TextRun(content="preset one")],
            bullet=BulletPreset(preset="BULLET_DISC_CIRCLE_SQUARE", nesting_level=1),
        ),
        Paragraph(
            elements=[TextRun(content="numbered")],
            bullet=BulletPreset(preset="NUMBERED_DECIMAL_ALPHA_ROMAN", nesting_level=1),
        ),
    ]
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    for paragraph in paragraphs:
        content.body.add_child(paragraph)

    xhtml = serialize_document(document)

    assert xhtml.count("<g:list ") == 3
    assert xhtml.count('<g:list g:list-id="list-1">') == 1
    assert xhtml.count('<g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">') == 1
    assert xhtml.count('<g:list g:bullet-preset="NUMBERED_DECIMAL_ALPHA_ROMAN">') == 1
    assert xhtml.count("<li") == 5
    assert xhtml.count("<g:bullet-style") == 2
    assert '<a href="https://example.com/bullet" />' in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    assert decoded.body.content[1:] == paragraphs


def test_rejects_invalid_mutated_paragraph_bullet() -> None:
    paragraph = Paragraph(elements=[TextRun(content="invalid")])
    paragraph.bullet = cast("Bullet | BulletPreset", object())
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(paragraph)

    with pytest.raises(ValueError, match="unsupported paragraph bullet object"):
        serialize_document(document)


def test_same_list_key_separated_by_paragraph_creates_two_groups() -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(
        Paragraph(elements=[TextRun(content="first")], bullet=Bullet(list_id="id"))
    )
    content.body.add_child(Paragraph(elements=[TextRun(content="separator")]))
    content.body.add_child(
        Paragraph(elements=[TextRun(content="second")], bullet=Bullet(list_id="id"))
    )

    xhtml = serialize_document(document)

    assert xhtml.count('<g:list g:list-id="id">') == 2
    assert xhtml.index("first") < xhtml.index("separator") < xhtml.index("second")


def test_accepts_bullet_style_metadata_after_item_paragraph() -> None:
    xhtml = xhtml_with_structure(
        '<g:list g:list-id="id"><li g:nesting-level="2">'
        '<p><span>item</span></p><g:bullet-style g:bold="true">'
        '<a href="https://example.com" /></g:bullet-style></li></g:list>'
    )

    decoded = deserialize_document(xhtml).tabs[0].content

    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    assert decoded.body.content[1] == Paragraph(
        elements=[TextRun(content="item")],
        style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
        bullet=Bullet(
            list_id="id",
            nesting_level=2,
            text_style=TextStyle(bold=True, link=UrlLink(url="https://example.com")),
        ),
    )


def test_normalizes_empty_existing_bullet_style_to_unset() -> None:
    paragraph = Paragraph(
        elements=[TextRun(content="item")],
        bullet=Bullet(list_id="list-1", text_style=TextStyle()),
    )
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(paragraph)

    xhtml = serialize_document(document)

    assert "<g:bullet-style" not in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    decoded_paragraph = decoded.body.content[1]
    assert isinstance(decoded_paragraph, Paragraph)
    assert isinstance(decoded_paragraph.bullet, Bullet)
    assert decoded_paragraph.bullet.text_style is UNSET


@pytest.mark.parametrize("invalid_start", [False, 0.0])
def test_rejects_non_integer_default_list_start_number(invalid_start: object) -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    level = ListLevel(glyph_format="%0", glyph_type="DECIMAL")
    level.start_number = invalid_start  # type: ignore[assignment]
    content.lists = {"list": ListDefinition(levels=[level])}

    with pytest.raises(ValueError, match="integer"):
        serialize_document(document)


def test_round_trips_complete_list_definitions_and_levels() -> None:
    lists = {
        "empty": ListDefinition(levels=[]),
        "list-1": ListDefinition(
            levels=[
                ListLevel(
                    glyph_format="%0.",
                    glyph_type="DECIMAL",
                    alignment="START",
                    indent_first_line=Dimension(magnitude=18, unit="PT"),
                    indent_start=Dimension(magnitude=36, unit="PT"),
                    start_number=1,
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
                ),
                ListLevel(
                    glyph_format="%1",
                    glyph_symbol="●",
                    alignment="CENTER",
                    indent_first_line=Dimension(magnitude=20, unit="PT"),
                    indent_start=Dimension(magnitude=40, unit="PT"),
                    start_number=0,
                ),
                ListLevel(
                    glyph_format="%2",
                    glyph_type="NONE",
                    alignment="END",
                    start_number=3,
                ),
                ListLevel(
                    glyph_format="%3",
                    glyph_type="GLYPH_TYPE_UNSPECIFIED",
                ),
            ]
        ),
    }
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    content.lists = lists

    xhtml = serialize_document(document)

    assert xhtml.index('g:list-id="empty"') < xhtml.index('g:list-id="list-1"')
    assert '<g:list-definition g:list-id="empty" />' in xhtml
    assert xhtml.count("<g:list-level") == 4
    assert '<a g:bookmark-id="bookmark-1" g:tab-id="tab-1" />' in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert list(decoded.lists) == ["empty", "list-1"]  # type: ignore[arg-type]
    assert decoded.lists == lists
    assert deserialize_document(serialize_document(document)) == document


@pytest.mark.parametrize(
    ("lists", "fragment"), [(UNSET, ""), ({}, "<g:list-definitions />")]
)
def test_preserves_unset_versus_empty_list_definitions(
    lists: object, fragment: str
) -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    content.lists = lists  # type: ignore[assignment]

    xhtml = serialize_document(document)

    assert ("<g:list-definitions" in xhtml) is bool(fragment)
    assert fragment in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert decoded.lists == lists


def xhtml_with_structure(structure: str, metadata: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Lists">'
        '<body><g:tab g:tab-id="tab" g:title="Main" g:index="0">'
        f"<g:document-tab>{metadata}<g:body><section><g:section-style />"
        f"{structure}"
        "</section></g:body></g:document-tab></g:tab></body></html>"
    )


@pytest.mark.parametrize(
    ("structure", "message"),
    [
        ('<g:list g:list-id="id" />', "at least one"),
        ("<g:list><li><p /></li></g:list>", "exactly one"),
        (
            '<g:list g:list-id="id" g:bullet-preset="BULLET_CHECKBOX">'
            "<li><p /></li></g:list>",
            "exactly one",
        ),
        (
            '<g:list g:bullet-preset="BULLET_CHECKBOX"><li>'
            "<g:bullet-style /><p /></li></g:list>",
            "forbidden",
        ),
        ('<g:list g:list-id="id"><li /></g:list>', "exactly one paragraph"),
        (
            '<g:list g:list-id="id"><li><p /><p /></li></g:list>',
            "exactly one paragraph",
        ),
        (
            '<g:list g:list-id="id"><li g:nesting-level="-1"><p /></li></g:list>',
            "non-negative",
        ),
        (
            '<g:list g:bullet-preset="NOT_A_PRESET"><li><p /></li></g:list>',
            "expected one of",
        ),
    ],
)
def test_rejects_invalid_structural_lists(structure: str, message: str) -> None:
    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml_with_structure(structure))


@pytest.mark.parametrize(
    ("structure", "message"),
    [
        (
            '<g:list g:list-id="id" g:unknown="x"><li><p /></li></g:list>',
            "unknown attribute g:unknown",
        ),
        (
            '<g:list g:list-id="id"><li><g:unknown /><p /></li></g:list>',
            "unknown child element g:unknown",
        ),
    ],
)
def test_rejects_unknown_list_or_item_content(structure: str, message: str) -> None:
    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml_with_structure(structure))


@pytest.mark.parametrize(
    ("structure", "diagnostic"),
    [
        (
            "<g:list />",
            "exactly one of g:list-id and g:bullet-preset is required",
        ),
        (
            '<g:list g:list-id="id"><li /></g:list>',
            "list item must contain exactly one paragraph",
        ),
        (
            '<g:list g:list-id="id"><li g:nesting-level="-1"><p /></li></g:list>',
            "nesting level must be non-negative",
        ),
        (
            '<g:list g:list-id="id">text<li><p /></li></g:list>',
            "unexpected text content",
        ),
        (
            '<g:list g:list-id="id"><li>text<p /></li></g:list>',
            "unexpected text content",
        ),
        (
            '<g:list g:list-id="id"><li><p />tail</li></g:list>',
            "unexpected text after child element",
        ),
        (
            '<g:list g:list-id="id"><li><p /></li>tail</g:list>',
            "unexpected text after child element",
        ),
    ],
)
def test_preserves_exact_list_validation_diagnostics(
    structure: str, diagnostic: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_structure(structure))

    assert str(error.value).endswith(f": {diagnostic}")
    assert "ListItemTag.children:" not in str(error.value)


@pytest.mark.parametrize(
    ("structure", "diagnostic"),
    [
        (
            "<g:list><li><p><g:unknown /></p></li></g:list>",
            "exactly one of g:list-id and g:bullet-preset is required",
        ),
        (
            '<g:list g:list-id="id" g:bullet-preset="BULLET_CHECKBOX">'
            "<li><p><g:unknown /></p></li></g:list>",
            "exactly one of g:list-id and g:bullet-preset is required",
        ),
        (
            '<g:list g:list-id="id"><li><p><g:unknown /></p><p /></li></g:list>',
            "list item must contain exactly one paragraph",
        ),
    ],
)
def test_list_preflight_errors_win_over_malformed_descendants(
    structure: str, diagnostic: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_structure(structure))

    assert str(error.value).endswith(f": {diagnostic}")


@pytest.mark.parametrize(
    ("structure", "diagnostic"),
    [
        (
            "<g:list>raw<li><p /></li></g:list>",
            "unexpected text content",
        ),
        (
            "<g:list><g:unknown /></g:list>",
            "unknown child element g:unknown",
        ),
        (
            '<g:list g:list-id="id"><li g:nesting-level="-1">raw<p /></li></g:list>',
            "unexpected text content",
        ),
    ],
)
def test_list_child_shell_errors_precede_semantic_validation(
    structure: str, diagnostic: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_structure(structure))

    assert str(error.value).endswith(f": {diagnostic}")


def test_negative_list_nesting_error_is_reported_at_item_path() -> None:
    structure = '<g:list g:list-id="id"><li g:nesting-level="-1"><p /></li></g:list>'

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_structure(structure))

    assert str(error.value).endswith("/li[1]: nesting level must be non-negative")
    assert "/@g:nesting-level" not in str(error.value)


@pytest.mark.parametrize(
    ("definitions", "message"),
    [
        ('<g:list-definitions g:unknown="x" />', "unknown attribute g:unknown"),
        (
            '<g:list-definitions><g:list-definition g:list-id="id">'
            '<g:list-level g:glyph-format="%0" g:glyph-symbol="x">'
            "<g:unknown /></g:list-level></g:list-definition></g:list-definitions>",
            "unknown child element g:unknown",
        ),
    ],
)
def test_rejects_unknown_list_definition_content(
    definitions: str, message: str
) -> None:
    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml_with_structure("", definitions))


def test_duplicate_second_list_definition_precedes_its_malformed_descendant() -> None:
    definitions = (
        "<g:list-definitions>"
        '<g:list-definition g:list-id="duplicate" />'
        '<g:list-definition g:list-id="duplicate"><g:unknown /></g:list-definition>'
        "</g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="duplicate list key 'duplicate'"):
        deserialize_document(xhtml_with_structure("", definitions))


def test_duplicate_list_definition_direct_tail_precedes_duplicate_key() -> None:
    definitions = (
        "<g:list-definitions>"
        '<g:list-definition g:list-id="duplicate" />'
        '<g:list-definition g:list-id="duplicate"><g:list-level '
        'g:glyph-format="%0" g:glyph-symbol="x" />tail</g:list-definition>'
        "</g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="unexpected text after child element"):
        deserialize_document(xhtml_with_structure("", definitions))


def test_malformed_first_list_definition_precedes_later_duplicate() -> None:
    definitions = (
        "<g:list-definitions>"
        '<g:list-definition g:list-id="duplicate"><g:unknown /></g:list-definition>'
        '<g:list-definition g:list-id="duplicate" />'
        "</g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="unknown child element g:unknown"):
        deserialize_document(xhtml_with_structure("", definitions))


@pytest.mark.parametrize(
    ("definitions", "message"),
    [
        ("<g:list-definitions>leading</g:list-definitions>", "unexpected text content"),
        (
            "<g:list-definitions>"
            '<g:list-definition g:list-id="id" />tail'
            "</g:list-definitions>",
            "unexpected text after child element",
        ),
    ],
)
def test_list_definition_wrapper_preserves_whitespace_messages(
    definitions: str, message: str
) -> None:
    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml_with_structure("", definitions))


def test_rejects_duplicate_list_definition_ids_instead_of_overwriting() -> None:
    definitions = (
        "<g:list-definitions>"
        '<g:list-definition g:list-id="duplicate" />'
        '<g:list-definition g:list-id="duplicate" />'
        "</g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="duplicate list key 'duplicate'"):
        deserialize_document(xhtml_with_structure("", definitions))


def test_list_level_identity_precedes_malformed_metadata_anchor() -> None:
    metadata = (
        '<g:list-definitions><g:list-definition g:list-id="id">'
        '<g:list-level g:glyph-format="%0"><a href="https://example.test">'
        "<g:unknown /></a></g:list-level>"
        "</g:list-definition></g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="exactly one"):
        deserialize_document(xhtml_with_structure("", metadata))


@pytest.mark.parametrize(
    ("level", "message"),
    [
        ('<g:list-level g:glyph-type="DECIMAL" />', "glyph-format"),
        ('<g:list-level g:glyph-format="%0" />', "exactly one"),
        (
            '<g:list-level g:glyph-format="%0" g:glyph-type="DECIMAL" '
            'g:glyph-symbol="x" />',
            "exactly one",
        ),
        (
            '<g:list-level g:glyph-format="%0" g:glyph-type="INVALID" />',
            "expected one of",
        ),
    ],
)
def test_rejects_invalid_list_levels(level: str, message: str) -> None:
    metadata = (
        '<g:list-definitions><g:list-definition g:list-id="id">'
        f"{level}</g:list-definition></g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml_with_structure("", metadata))


def document_with_table(table: Table) -> Document:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(table)
    return document


def xhtml_with_table_tree(table_tree: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Tables">'
        '<body><g:tab g:tab-id="tab" g:title="Main" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style />"
        f"{table_tree}"
        "</section></g:body></g:document-tab></g:tab></body></html>"
    )


def decoded_table(document: Document) -> Table:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    table = content.body.content[1]
    assert isinstance(table, Table)
    return table


@pytest.mark.parametrize("key_field", ["table_key", "row_key", "cell_key"])
def test_rejects_invalid_mutated_table_keys(key_field: str) -> None:
    cell = TableCell(content=[])
    row = TableRow(cells=[cell])
    table = Table(rows=[row])
    owner = {"table_key": table, "row_key": row, "cell_key": cell}[key_field]
    setattr(owner, key_field, UNSET)

    with pytest.raises(ValueError, match="must be a string"):
        serialize_document(document_with_table(table))


def test_round_trips_complete_recursive_table() -> None:
    border = TableCellBorder(
        color=Color(red=0.1, green=0.2, blue=0.3),
        width=Dimension(magnitude=1.5, unit="PT"),
        dash_style="SOLID",
    )
    styled_cell = TableCell(
        cell_key="merged-cell",
        style=TableCellStyle(
            row_span=2,
            column_span=2,
            background_color=Color(red=0.4, green=0.5, blue=0.6),
            border_left=border,
            border_right=border,
            border_top=border,
            border_bottom=border,
            padding_left=Dimension(magnitude=6, unit="PT"),
            padding_right=Dimension(magnitude=7, unit="PT"),
            padding_top=Dimension(magnitude=4, unit="PT"),
            padding_bottom=Dimension(magnitude=5, unit="PT"),
            content_alignment="MIDDLE",
        ),
        content=[
            Paragraph(elements=[TextRun(content="Cell paragraph")]),
            Table(rows=[TableRow(cells=[TableCell(content=[])])]),
            TableOfContents(content=[Paragraph(elements=[TextRun(content="TOC")])]),
        ],
    )
    table = Table(
        table_key="table-1",
        column_styles=[
            TableColumn(
                width_type="FIXED_WIDTH", width=Dimension(magnitude=144, unit="PT")
            ),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
        rows=[
            TableRow(
                row_key="header-row",
                min_height=Dimension(magnitude=24, unit="PT"),
                prevent_overflow=True,
                is_header=True,
                cells=[
                    styled_cell,
                    TableCell(
                        cell_key="transparent-cell",
                        style=TableCellStyle(background_color=None),
                        content=[],
                    ),
                ],
            ),
            TableRow(cells=[], is_header=False),
        ],
    )

    xhtml = serialize_document(document_with_table(table))

    assert '<table g:table-key="table-1">' in xhtml
    assert '<col g:width-type="FIXED_WIDTH" g:width="144" />' in xhtml
    assert '<col g:width-type="EVENLY_DISTRIBUTED" />' in xhtml
    assert xhtml.index("<colgroup>") < xhtml.index("<tbody>")
    assert (
        '<tr g:row-key="header-row" g:min-height="24" '
        'g:prevent-overflow="true" g:is-header="true">'
    ) in xhtml
    assert '<td g:cell-key="merged-cell" rowspan="2" colspan="2">' in xhtml
    for fragment in (
        'g:content-alignment="MIDDLE"',
        'g:padding-left="6"',
        'g:padding-right="7"',
        'g:padding-top="4"',
        'g:padding-bottom="5"',
        '<g:background-color g:red="0.4" g:green="0.5" g:blue="0.6" />',
        '<g:border-left g:dash-style="SOLID" g:width="1.5">',
        '<g:border-right g:dash-style="SOLID" g:width="1.5">',
        '<g:border-top g:dash-style="SOLID" g:width="1.5">',
        '<g:border-bottom g:dash-style="SOLID" g:width="1.5">',
        '<g:color g:red="0.1" g:green="0.2" g:blue="0.3" />',
        '<g:background-color g:transparent="true" />',
        '<tr g:is-header="false" />',
    ):
        assert fragment in xhtml
    assert xhtml.count("<table") == 2
    expected_document = document_with_table(table)
    decoded_document = deserialize_document(xhtml)
    assert decoded_document == expected_document
    assert decoded_table(decoded_document) == table
    assert decoded_table(decoded_document).rows[0].is_header is True
    assert decoded_table(decoded_document).rows[1].is_header is False


def test_accepts_table_and_cell_metadata_after_content_without_reordering() -> None:
    xhtml = xhtml_with_table_tree(
        "<table><tbody><tr><td>"
        "<g:paragraph><span>first</span></g:paragraph>"
        '<g:cell-style g:content-alignment="BOTTOM" />'
        "<g:paragraph><span>second</span></g:paragraph>"
        "</td></tr></tbody>"
        '<colgroup><col g:width-type="EVENLY_DISTRIBUTED" /></colgroup>'
        "</table>"
    )
    expected = Table(
        column_styles=[TableColumn(width_type="EVENLY_DISTRIBUTED")],
        rows=[
            TableRow(
                cells=[
                    TableCell(
                        content=[
                            Paragraph(elements=[TextRun(content="first")]),
                            Paragraph(elements=[TextRun(content="second")]),
                        ],
                        style=TableCellStyle(content_alignment="BOTTOM"),
                    )
                ]
            )
        ],
    )

    assert decoded_table(deserialize_document(xhtml)) == expected


def test_rejects_duplicate_singular_metadata_separated_by_content() -> None:
    table = (
        "<table><tbody><tr><td><g:cell-style /><p><span>content</span></p>"
        "<g:cell-style /></td></tr></tbody></table>"
    )

    with pytest.raises(XHTMLParseError, match="at most one g:cell-style"):
        deserialize_document(xhtml_with_table_tree(table))


@pytest.mark.parametrize(
    ("table_tree", "diagnostic"),
    [
        ("<table><colgroup /></table>", "missing required tbody child"),
        (
            "<table><tbody><tr><td><g:cell-style><g:border-left "
            'g:dash-style="SOLID" g:width="1" /></g:cell-style></td></tr></tbody>'
            "</table>",
            "missing required g:color child",
        ),
    ],
)
def test_preserves_missing_required_table_child_diagnostics(
    table_tree: str, diagnostic: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_table_tree(table_tree))

    assert str(error.value).endswith(f": {diagnostic}")


def test_rejects_unknown_table_child() -> None:
    xhtml = xhtml_with_table_tree("<table><caption /><tbody /></table>")

    with pytest.raises(XHTMLParseError, match="unknown child element caption"):
        deserialize_document(xhtml)


@pytest.mark.parametrize(("columns", "fragment"), [(UNSET, ""), ([], "<colgroup />")])
def test_preserves_unset_versus_empty_table_columns(
    columns: object, fragment: str
) -> None:
    table = Table(rows=[], column_styles=columns)  # type: ignore[arg-type]

    xhtml = serialize_document(document_with_table(table))

    assert ("<colgroup" in xhtml) is bool(fragment)
    assert fragment in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    decoded_table = decoded.body.content[1]
    assert isinstance(decoded_table, Table)
    assert decoded_table.column_styles == columns


def test_normalizes_default_only_table_cell_style_to_unset() -> None:
    table = Table(
        rows=[TableRow(cells=[TableCell(content=[], style=TableCellStyle())])]
    )

    decoded = deserialize_document(serialize_document(document_with_table(table)))

    content = decoded.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    decoded_table = content.body.content[1]
    assert isinstance(decoded_table, Table)
    assert decoded_table.rows[0].cells[0].style is UNSET


@pytest.mark.parametrize("attribute", ['rowspan="1"', 'colspan="1"'])
def test_malformed_cell_descendant_precedes_explicit_default_span(
    attribute: str,
) -> None:
    table = f"<table><tbody><tr><td {attribute}><g:unknown /></td></tr></tbody></table>"

    with pytest.raises(XHTMLParseError, match="unknown structural element g:unknown"):
        deserialize_document(xhtml_with_table_tree(table))


@pytest.mark.parametrize("attribute", ['rowspan="1"', 'colspan="1"'])
def test_rejects_explicit_default_cell_span(attribute: str) -> None:
    xhtml = serialize_document(
        document_with_table(Table(rows=[TableRow(cells=[TableCell(content=[])])]))
    ).replace("<td />", f"<td {attribute} />")

    with pytest.raises(XHTMLParseError, match="must be greater than 1"):
        deserialize_document(xhtml)


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ('g:width-type="FIXED_WIDTH"', 'g:width-type="FIXED_WIDTH"'),
        (
            'g:width-type="EVENLY_DISTRIBUTED"',
            'g:width-type="EVENLY_DISTRIBUTED" g:width="10"',
        ),
    ],
)
def test_rejects_invalid_table_column_width(column: str, replacement: str) -> None:
    width = Dimension(magnitude=10) if "FIXED_WIDTH" in column else UNSET
    table = Table(
        rows=[],
        column_styles=[TableColumn(width_type=column.split('"')[1], width=width)],  # type: ignore[arg-type]
    )
    xhtml = serialize_document(document_with_table(table))
    if "FIXED_WIDTH" in column:
        xhtml = xhtml.replace(' g:width="10"', "")
    else:
        xhtml = xhtml.replace(column, replacement)

    with pytest.raises(XHTMLParseError, match="width"):
        deserialize_document(xhtml)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            '<g:background-color g:red="0.1" g:green="0.2" g:blue="0.3" />',
            '<g:background-color g:red="0.1" />',
            "requires red, green, and blue",
        ),
        (' g:width="1"', "", "missing required attribute"),
    ],
)
def test_rejects_invalid_table_cell_color_or_border(
    old: str, new: str, message: str
) -> None:
    border = TableCellBorder(
        color=Color(red=0, green=0, blue=0),
        width=Dimension(magnitude=1),
        dash_style="SOLID",
    )
    table = Table(
        rows=[
            TableRow(
                cells=[
                    TableCell(
                        content=[],
                        style=TableCellStyle(
                            background_color=Color(red=0.1, green=0.2, blue=0.3),
                            border_left=border,
                        ),
                    )
                ]
            )
        ]
    )
    xhtml = serialize_document(document_with_table(table)).replace(old, new, 1)

    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml)
