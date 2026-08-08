from typing import Any

import pytest

from gdocs_patch.xhtml import XHTMLParseError, deserialize_document
from gdocs_patch.xhtml.attributes import (
    IntegerAttribute,
    NonNegativeIntegerAttribute,
    PositiveIntegerAttribute,
)

_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>\n'


@pytest.mark.parametrize(
    "attribute_type",
    [IntegerAttribute, NonNegativeIntegerAttribute, PositiveIntegerAttribute],
)
@pytest.mark.parametrize("value", [1.5, float("nan"), float("inf"), "1", None])
def test_integer_attribute_encoders_reject_non_integer_runtime_values(
    attribute_type: type[IntegerAttribute], value: Any
) -> None:
    with pytest.raises(TypeError, match="expected int"):
        attribute_type().encode(value)


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
