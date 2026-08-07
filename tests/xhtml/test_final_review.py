from collections.abc import Callable

import pytest

from gdocs_patch.models import (
    Body,
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
    SectionStyle,
    Tab,
    Table,
    TableCell,
    TableCellStyle,
    TableColumn,
    TableRow,
    TextRun,
    TextStyle,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document
from gdocs_patch.xhtml import base as base_module
from gdocs_patch.xhtml import decoder as decoder_module

DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def xhtml(structure: str = "") -> str:
    return (
        DECLARATION + '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Title">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style />"
        f"{structure}</section></g:body></g:document-tab></g:tab></body></html>"
    )


def model_document() -> Document:
    return Document(
        document_id="doc",
        title="Title",
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
                            Paragraph(elements=[TextRun(content="text")]),
                        ]
                    )
                ),
            )
        ],
    )


@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE html [<!ENTITY internal "expanded">]>',
        '<!DOCTYPE html SYSTEM "https://example.test/external.dtd">',
        '<!ENTITY stray "value">',
    ],
)
def test_rejects_dtd_and_entity_declarations_before_expansion(declaration: str) -> None:
    source = xhtml("<p><span>&internal;</span></p>")
    source = source.replace("<html ", declaration + "<html ")

    with pytest.raises(XHTMLParseError, match="DTD|entity"):
        deserialize_document(source)


def test_rejects_input_over_named_character_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(decoder_module, "MAX_XHTML_INPUT_CHARACTERS", 100)

    with pytest.raises(XHTMLParseError, match="100 characters"):
        deserialize_document(xhtml())


def nested_xml(depth: int) -> str:
    return DECLARATION + "<x>" * depth + "</x>" * depth


def test_element_depth_limit_accepts_boundary_before_grammar_validation() -> None:
    with pytest.raises(XHTMLParseError, match="expected XHTML"):
        deserialize_document(nested_xml(decoder_module.MAX_XML_ELEMENT_DEPTH))


def test_element_depth_limit_rejects_excess_without_recursion_error() -> None:
    with pytest.raises(XHTMLParseError, match="element depth") as error:
        deserialize_document(nested_xml(decoder_module.MAX_XML_ELEMENT_DEPTH + 1))

    assert not isinstance(error.value.__cause__, RecursionError)


@pytest.mark.parametrize("location", ["title", "attribute", "text", "tail"])
@pytest.mark.parametrize("invalid", ["\x00", "\x0b", "\ud800"])
def test_serializer_rejects_illegal_xml_10_characters(
    location: str, invalid: str
) -> None:
    document = model_document()
    if location == "title":
        document.title = invalid
    elif location == "attribute":
        document.tabs[0].title = invalid
    else:
        run = document.tabs[0].content.body.content[1].elements[0]  # type: ignore[union-attr]
        assert isinstance(run, TextRun)
        run.content = invalid if location == "text" else "line\n" + invalid

    with pytest.raises(ValueError, match="XML 1.0"):
        serialize_document(document)


Mutation = Callable[[Document], None]


def mutate_tab_level(document: Document) -> None:
    document.tabs[0].nesting_level = -1


def mutate_bullet_level(document: Document) -> None:
    paragraph = document.tabs[0].content.body.content[1]  # type: ignore[union-attr]
    assert isinstance(paragraph, Paragraph)
    paragraph.bullet = BulletPreset(preset="BULLET_CHECKBOX", nesting_level=-1)


def mutate_bad_preset(document: Document) -> None:
    paragraph = document.tabs[0].content.body.content[1]  # type: ignore[union-attr]
    assert isinstance(paragraph, Paragraph)
    paragraph.bullet = BulletPreset(preset="BULLET_CHECKBOX")
    paragraph.bullet.preset = "INVALID"  # type: ignore[assignment,union-attr]


def mutate_bad_named_style(document: Document) -> None:
    paragraph = document.tabs[0].content.body.content[1]  # type: ignore[union-attr]
    assert isinstance(paragraph, Paragraph)
    paragraph.style = ParagraphStyle(named_style_type="NORMAL_TEXT")
    paragraph.style.named_style_type = "INVALID"  # type: ignore[assignment,union-attr]


def mutate_bad_color(document: Document) -> None:
    paragraph = document.tabs[0].content.body.content[1]  # type: ignore[union-attr]
    assert isinstance(paragraph, Paragraph)
    run = paragraph.elements[0]
    assert isinstance(run, TextRun)
    color = Color(red=0, green=0, blue=0)
    run.text_style = TextStyle(foreground_color=color)
    color.red = 2


def mutate_bad_span(document: Document) -> None:
    table = Table(
        rows=[TableRow(cells=[TableCell(content=[], style=TableCellStyle())])]
    )
    document.tabs[0].content.body.content.append(table)  # type: ignore[union-attr]
    table.rows[0].cells[0].style.row_span = 0  # type: ignore[union-attr]


def mutate_bad_column(document: Document) -> None:
    table = Table(rows=[], column_styles=[TableColumn(width_type="EVENLY_DISTRIBUTED")])
    document.tabs[0].content.body.content.append(table)  # type: ignore[union-attr]
    table.column_styles[0].width = Dimension(magnitude=1, unit="PT")  # type: ignore[index]


def mutate_bad_list_level(document: Document) -> None:
    level = ListLevel(glyph_format="%0", glyph_symbol="x")
    level.glyph_type = "DECIMAL"
    document.tabs[0].content.lists = {"id": ListDefinition(levels=[level])}  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "mutation",
    [
        mutate_tab_level,
        mutate_bullet_level,
        mutate_bad_preset,
        mutate_bad_named_style,
        mutate_bad_color,
        mutate_bad_span,
        mutate_bad_column,
        mutate_bad_list_level,
    ],
)
def test_encoder_rejects_mutated_state_that_decoder_would_reject(
    mutation: Mutation,
) -> None:
    document = model_document()
    mutation(document)

    with pytest.raises(ValueError):
        serialize_document(document)


@pytest.mark.parametrize(
    "value",
    [" 1", "1 ", "+1", "01", "1_0", "-0"],
)
def test_rejects_noncanonical_integer_lexemes(value: str) -> None:
    with pytest.raises(XHTMLParseError, match="integer"):
        deserialize_document(xhtml().replace('g:index="0"', f'g:index="{value}"'))


@pytest.mark.parametrize(
    "value",
    [
        " 1",
        "1 ",
        "+1",
        "01",
        "1_0",
        "nan",
        "NaN",
        "inf",
        "Infinity",
        ".5",
        "1.",
        "1E2",
        "0x1p0",
    ],
)
def test_rejects_noncanonical_float_lexemes(value: str) -> None:
    source = xhtml(f'<p><span g:font-size="{value}">x</span></p>')
    with pytest.raises(XHTMLParseError, match="float"):
        deserialize_document(source)


@pytest.mark.parametrize(
    "value", [0.0, -0.0, 1.0, -1.25, 1e-07, 1e20, 1.2345678901234567]
)
def test_format_number_is_canonical_and_idempotent(value: float) -> None:
    encoded = base_module.format_number(value)
    parsed = base_module.parse_float(encoded, "/test")

    assert base_module.format_number(parsed) == encoded
