import pytest

from gdocs_patch.xhtml import XHTMLParseError, deserialize_document

_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def _document(structure: str = "", *, metadata: str = "") -> str:
    return (
        _DECLARATION + '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Framework">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        f"<g:document-tab>{metadata}<g:body><section><g:section-style />"
        f"{structure}</section></g:body></g:document-tab>"
        "</g:tab></body></html>"
    )


@pytest.mark.parametrize(
    ("xhtml", "path"),
    [
        (
            _document('<p><g:paragraph-style g:unknown="x" /></p>'),
            "/g:paragraph-style",
        ),
        (_document('<p><span g:bold="yes">x</span></p>'), "/@g:bold"),
        (
            _document('<p><span g:baseline-offset="HIGH">x</span></p>'),
            "/@g:baseline-offset",
        ),
        (_document("<p><g:auto-text /></p>"), "/g:auto-text[1]"),
        (
            _document().replace('g:index="0"', 'g:index="0" g:nesting-level="-1"'),
            "/@g:nesting-level",
        ),
    ],
)
def test_invalid_declarative_fields_have_contextual_paths(
    xhtml: str, path: str
) -> None:
    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert path in str(error.value)


def test_attribute_order_is_irrelevant_when_decoding() -> None:
    source = (
        _DECLARATION + '<html g:title="Title" xmlns:g="urn:gdocs-patch:xhtml:1" '
        'g:document-id="doc" xmlns="http://www.w3.org/1999/xhtml">'
        '<body><g:tab g:index="0" g:title="Tab" g:tab-id="tab">'
        "<g:document-tab /></g:tab></body></html>"
    )

    document = deserialize_document(source)

    assert document.document_id == "doc"
    assert document.tabs[0].tab_id == "tab"


@pytest.mark.parametrize(
    ("xhtml", "message"),
    [
        (
            _document(
                "<g:table-of-contents><section><g:section-style /></section>"
                "</g:table-of-contents>"
            ),
            "element is not permitted under this parent",
        ),
        (
            _document().replace("</body></html>", "</body><body /></html>"),
            "expected at most one body child",
        ),
        (
            _document("<table><colgroup /></table>"),
            "expected at least one tbody child",
        ),
        (
            _document().replace(
                "<g:body><section><g:section-style /></section></g:body>",
                "<g:body />",
            ),
            "expected at least one child element",
        ),
        (
            _document("<p><g:paragraph-style />BAD<span>ok</span></p>"),
            "text is not permitted under this parent",
        ),
    ],
)
def test_declarative_child_constraints(xhtml: str, message: str) -> None:
    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml)


def test_repeated_child_error_path_uses_one_based_index() -> None:
    xhtml = _document('<p><span>valid</span><span g:bold="yes">invalid</span></p>')

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/span[2]/@g:bold" in str(error.value)


def test_semantic_error_uses_automatic_source_location() -> None:
    structure = (
        '<g:list g:bullet-preset="BULLET_CHECKBOX">\n'
        "<li>\n"
        "<g:bullet-style />\n"
        "<p />\n"
        "</li>\n"
        "</g:list>"
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(_document(structure))

    assert str(error.value).startswith(
        "/html/body/g:tab[1]/g:document-tab/g:body/section[1]/g:list[1]/li[1]"
        "/g:bullet-style (line 4, column 1):"
    )


def test_unique_children_reject_duplicate_keys() -> None:
    metadata = (
        "<g:list-definitions>"
        '<g:list-definition g:list-id="duplicate" />'
        '<g:list-definition g:list-id="duplicate" />'
        "</g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(_document(metadata=metadata))

    assert str(error.value).endswith(": duplicate child key 'duplicate'")
    assert "ListDefinitionsTag.children" not in str(error.value)
