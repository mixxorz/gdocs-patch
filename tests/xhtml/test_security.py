from collections.abc import Callable

import pytest

from gdocs_patch.models import (
    Body,
    BulletPreset,
    Color,
    Document,
    DocumentTab,
    Paragraph,
    SectionBreak,
    SectionStyle,
    Tab,
    Table,
    TableCell,
    TableCellStyle,
    TableOfContents,
    TableRow,
    TextRun,
    TextStyle,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document

DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'
MAX_XHTML_CHARACTERS = 10_000_000
MAX_ELEMENT_DEPTH = 256


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


def text_run(document: Document) -> TextRun:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)
    run = paragraph.elements[0]
    assert isinstance(run, TextRun)
    return run


@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE html [<!ENTITY internal "expanded">]>',
        '<!DOCTYPE html SYSTEM "https://example.test/external.dtd">',
        '<!ENTITY stray "value">',
    ],
)
def test_rejects_dtd_and_entity_declarations(declaration: str) -> None:
    source = xhtml("<p><span>&internal;</span></p>").replace(
        "<html ", declaration + "<html "
    )

    with pytest.raises(XHTMLParseError, match="DTD|entity"):
        deserialize_document(source)


def test_documented_character_limit_accepts_boundary_and_rejects_excess() -> None:
    source = xhtml()
    at_input_limit = source + " " * (MAX_XHTML_CHARACTERS - len(source))
    assert deserialize_document(at_input_limit).document_id == "doc"
    with pytest.raises(XHTMLParseError, match="10000000 characters"):
        deserialize_document(at_input_limit + " ")

    document = model_document()
    document.title = ""
    base_length = len(serialize_document(document))
    document.title = "x" * (MAX_XHTML_CHARACTERS - base_length)
    at_output_limit = serialize_document(document)
    assert len(at_output_limit) == MAX_XHTML_CHARACTERS
    assert deserialize_document(at_output_limit) == document
    document.title += "x"
    with pytest.raises(ValueError, match="10000000 characters"):
        serialize_document(document)


def nested_xml(depth: int) -> str:
    return DECLARATION + "<x>" * depth + "</x>" * depth


def document_with_table_of_contents_depth(depth: int) -> Document:
    document = model_document()
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    nested: list[TableOfContents] = []
    for _ in range(depth):
        nested = [TableOfContents(content=nested)]
    content.body.content[:] = [SectionBreak(style=SectionStyle()), *nested]
    return document


def test_documented_element_depth_accepts_boundary_and_rejects_excess() -> None:
    with pytest.raises(XHTMLParseError, match="expected XHTML"):
        deserialize_document(nested_xml(MAX_ELEMENT_DEPTH))
    with pytest.raises(XHTMLParseError, match="element depth") as error:
        deserialize_document(nested_xml(MAX_ELEMENT_DEPTH + 1))
    assert not isinstance(error.value.__cause__, RecursionError)

    # The document envelope contributes six levels, leaving 250 nested TOCs.
    boundary = document_with_table_of_contents_depth(MAX_ELEMENT_DEPTH - 6)
    assert deserialize_document(serialize_document(boundary)) == boundary
    excess = document_with_table_of_contents_depth(MAX_ELEMENT_DEPTH - 5)
    with pytest.raises(ValueError, match="element depth") as error:
        serialize_document(excess)
    assert not isinstance(error.value.__cause__, RecursionError)


@pytest.mark.parametrize("channel", ["attribute", "text", "tail"])
def test_serializer_rejects_illegal_xml_character_in_output_channel(
    channel: str,
) -> None:
    document = model_document()
    if channel == "attribute":
        document.tabs[0].title = "\x00"
    elif channel == "text":
        text_run(document).content = "\x00"
    else:
        text_run(document).content = "line\n\x00"

    with pytest.raises(ValueError, match="XML 1.0"):
        serialize_document(document)


def mutate_nested_enum(document: Document) -> None:
    paragraph = document.tabs[0].content.body.content[1]  # type: ignore[union-attr]
    assert isinstance(paragraph, Paragraph)
    paragraph.bullet = BulletPreset(preset="BULLET_CHECKBOX")
    paragraph.bullet.preset = "INVALID"  # type: ignore[assignment,union-attr]


def mutate_nested_range(document: Document) -> None:
    run = text_run(document)
    run.text_style = TextStyle(foreground_color=Color(red=0, green=0, blue=0))
    run.text_style.foreground_color.red = 2  # type: ignore[union-attr]


def mutate_nested_span(document: Document) -> None:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    style = TableCellStyle(row_span=2)
    style.row_span = 0
    content.body.content.append(
        Table(rows=[TableRow(cells=[TableCell(content=[], style=style)])])
    )


def mutate_nested_collection(document: Document) -> None:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    content.named_styles = ()  # type: ignore[assignment]


@pytest.mark.parametrize(
    "mutation",
    [
        mutate_nested_enum,
        mutate_nested_range,
        mutate_nested_span,
        mutate_nested_collection,
    ],
)
def test_serializer_rejects_representative_invalid_nested_model_state(
    mutation: Callable[[Document], None],
) -> None:
    document = model_document()
    mutation(document)

    with pytest.raises(ValueError):
        serialize_document(document)


@pytest.mark.parametrize(
    ("attribute", "value", "kind"),
    [("g:index", "+1", "integer"), ("g:font-size", "1.00", "float")],
)
def test_rejects_noncanonical_numeric_lexemes(
    attribute: str, value: str, kind: str
) -> None:
    source = (
        xhtml().replace('g:index="0"', f'g:index="{value}"')
        if attribute == "g:index"
        else xhtml(f'<p><span g:font-size="{value}">x</span></p>')
    )

    with pytest.raises(XHTMLParseError, match=kind):
        deserialize_document(source)
