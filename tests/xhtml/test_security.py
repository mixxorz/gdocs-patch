import pytest

from gdocs_patch.xhtml import XHTMLParseError, deserialize_document

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


def test_wraps_invalid_unicode_input_as_xhtml_parse_error() -> None:
    with pytest.raises(XHTMLParseError, match="malformed XML") as error:
        deserialize_document(DECLARATION + "<html>\ud800</html>")

    assert isinstance(error.value.__cause__, UnicodeEncodeError)


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


def test_documented_input_character_limit_accepts_boundary_and_rejects_excess() -> None:
    source = xhtml()
    at_input_limit = source + " " * (MAX_XHTML_CHARACTERS - len(source))
    assert deserialize_document(at_input_limit).document_id == "doc"
    with pytest.raises(XHTMLParseError, match="10000000 characters"):
        deserialize_document(at_input_limit + " ")


def nested_xml(depth: int) -> str:
    return DECLARATION + "<x>" * depth + "</x>" * depth


def test_documented_input_element_depth_rejects_excess() -> None:
    with pytest.raises(XHTMLParseError, match="element depth") as error:
        deserialize_document(nested_xml(MAX_ELEMENT_DEPTH + 1))
    assert not isinstance(error.value.__cause__, RecursionError)


@pytest.mark.parametrize(
    ("attribute", "value", "kind"),
    [
        ("g:index", "+1", "integer"),
        ("g:font-size", "1.00", "float"),
        ("g:font-size", "1e9999", "finite form"),
    ],
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
