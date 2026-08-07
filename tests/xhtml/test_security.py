from collections.abc import Callable

import pytest

from gdocs_patch.models import (
    Body,
    Document,
    DocumentTab,
    Paragraph,
    SectionBreak,
    SectionStyle,
    Tab,
    TableOfContents,
    TextRun,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document

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
def test_rejects_dtd_and_entity_declarations(declaration: str) -> None:
    source = xhtml("<p><span>&internal;</span></p>").replace(
        "<html ", declaration + "<html "
    )

    with pytest.raises(XHTMLParseError, match="DTD|entity"):
        deserialize_document(source)


def test_rejects_input_over_documented_character_limit() -> None:
    with pytest.raises(XHTMLParseError, match="10000000 characters"):
        deserialize_document(xhtml() + " " * 10_000_000)


def test_rejects_input_over_documented_element_depth_limit() -> None:
    source = DECLARATION + "<x>" * 257 + "</x>" * 257

    with pytest.raises(XHTMLParseError, match="element depth") as error:
        deserialize_document(source)

    assert not isinstance(error.value.__cause__, RecursionError)


def test_serializer_rejects_output_over_documented_character_limit() -> None:
    document = model_document()
    document.title = "x" * 10_000_000

    with pytest.raises(ValueError, match="10000000 characters"):
        serialize_document(document)


def test_serializer_rejects_output_over_documented_element_depth_limit() -> None:
    document = model_document()
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    nested: list[TableOfContents] = []
    for _ in range(251):
        nested = [TableOfContents(content=nested)]
    content.body.content[:] = [SectionBreak(style=SectionStyle()), *nested]

    with pytest.raises(ValueError, match="element depth") as error:
        serialize_document(document)

    assert not isinstance(error.value.__cause__, RecursionError)


@pytest.mark.parametrize("invalid", ["\x00", "\ud800"])
def test_serializer_rejects_illegal_xml_10_characters(invalid: str) -> None:
    document = model_document()
    document.title = invalid

    with pytest.raises(ValueError, match="XML 1.0"):
        serialize_document(document)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda document: setattr(document, "title", 1),
        lambda document: setattr(document, "tabs", "not-a-list"),
    ],
)
def test_serializer_rejects_invalid_mutated_model_state(
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
