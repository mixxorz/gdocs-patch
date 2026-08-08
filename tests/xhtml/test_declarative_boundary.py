from typing import Any

import pytest

from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, tags
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


def test_all_paragraph_vocabulary_is_declarative() -> None:
    paragraph_tags = (
        tags.GenericParagraphTag,
        tags.UnspecifiedParagraphTag,
        tags.ParagraphTag,
        tags.TitleTag,
        tags.SubtitleTag,
        tags.Heading1Tag,
        tags.Heading2Tag,
        tags.Heading3Tag,
        tags.Heading4Tag,
        tags.Heading5Tag,
        tags.Heading6Tag,
    )

    assert all(not issubclass(tag, tags._OpaqueStructuralTag) for tag in paragraph_tags)
    assert "payload" not in tags.ParagraphTag.fields()
    assert (
        tags.PositionedObjectsTag.fields()["children"].specs[0].node_type
        is tags.PositionedObjectTag
    )
    assert tags.ContentAnchorTag.fields()["children"].max_num == 1
    assert tags.AutoTextTag.fields()["auto_text_type"].required
    assert tags.RichLinkTag.fields()["uri"].required


def test_lists_are_fully_declarative() -> None:
    assert not issubclass(tags.ListTag, tags._OpaqueStructuralTag)
    assert "payload" not in tags.ListTag.fields()
    assert tags.ListTag.fields()["children"].specs[0].node_type is tags.ListItemTag
    assert tags.ListTag.fields()["children"].min_num == 1

    list_id = tags.ListTag.fields()["list_id"]
    bullet_preset = tags.ListTag.fields()["bullet_preset"]
    nesting_level = tags.ListItemTag.fields()["nesting_level"]
    item_children = tags.ListItemTag.fields()["children"]

    assert list_id.bound_xml_name.endswith("list-id")
    assert bullet_preset.bound_xml_name.endswith("bullet-preset")
    assert nesting_level.default == 0
    assert item_children.min_num == 1
    assert any(spec.node_type is tags.BulletStyleTag for spec in item_children.specs)
    assert any(spec.node_type is tags.ParagraphTag for spec in item_children.specs)


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
