import pytest

from gdocs_patch.xhtml import XHTMLParseError, deserialize_document

_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


def test_repeated_child_decode_error_path_includes_one_based_index() -> None:
    xhtml = (
        _DECLARATION + '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Paths">'
        '<body><g:tab g:tab-id="tab" g:title="Tab" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style />"
        '<p><span>valid</span><span g:bold="yes">invalid</span></p>'
        "</section></g:body></g:document-tab></g:tab></body></html>"
    )

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml)

    assert "/span[2]/@g:bold" in str(error.value)
