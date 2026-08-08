import re
import sys
from dataclasses import dataclass
from typing import Any, Literal, Never, cast
from xml.etree import ElementTree
from xml.parsers import expat

from gdocs_patch import models

from . import tags
from .base import (
    GDOCS_NAMESPACE,
    MAX_ELEMENT_DEPTH,
    MAX_XHTML_CHARACTERS,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    XHTMLParseError,
    construct_model,
    decode_link,
    display_name,
    extract_one_child,
    gdocs_name,
    optional_string,
    parse_allowed,
    parse_boolean,
    parse_error,
    parse_float,
    parse_integer,
    parse_text_style,
    required_string,
    text_style_attributes,
    validate_attributes,
    validate_whitespace,
    xhtml_name,
)
from .nodes import DecodeError, Node, Tag, Text
from .nodes import Decoder as XHTMLDecoder

_PARAGRAPH_TAGS = {
    gdocs_name("paragraph"): models.UNSET,
    gdocs_name("named-style-unspecified"): "NAMED_STYLE_TYPE_UNSPECIFIED",
    xhtml_name("p"): "NORMAL_TEXT",
    gdocs_name("title"): "TITLE",
    gdocs_name("subtitle"): "SUBTITLE",
    **{xhtml_name(f"h{level}"): f"HEADING_{level}" for level in range(1, 7)},
}
_NAMED_STYLE_TYPES = {
    "NAMED_STYLE_TYPE_UNSPECIFIED",
    "NORMAL_TEXT",
    "TITLE",
    "SUBTITLE",
    "HEADING_1",
    "HEADING_2",
    "HEADING_3",
    "HEADING_4",
    "HEADING_5",
    "HEADING_6",
}
_DIRECTIONS = {"CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"}
_DASH_STYLES = {"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"}
_DATE_FORMATS = {
    "DATE_FORMAT_UNSPECIFIED",
    "DATE_FORMAT_CUSTOM",
    "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
    "DATE_FORMAT_MONTH_DAY_FULL",
    "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
    "DATE_FORMAT_ISO8601",
}
_BULLET_PRESETS = {
    "BULLET_GLYPH_PRESET_UNSPECIFIED",
    "BULLET_DISC_CIRCLE_SQUARE",
    "BULLET_DIAMONDX_ARROW3D_SQUARE",
    "BULLET_CHECKBOX",
    "BULLET_ARROW_DIAMOND_DISC",
    "BULLET_STAR_CIRCLE_SQUARE",
    "BULLET_ARROW3D_CIRCLE_SQUARE",
    "BULLET_LEFTTRIANGLE_DIAMOND_DISC",
    "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE",
    "BULLET_DIAMOND_CIRCLE_SQUARE",
    "NUMBERED_DECIMAL_ALPHA_ROMAN",
    "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
    "NUMBERED_DECIMAL_NESTED",
    "NUMBERED_UPPERALPHA_ALPHA_ROMAN",
    "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
    "NUMBERED_ZERODECIMAL_ALPHA_ROMAN",
}
_TIME_FORMATS = {
    "TIME_FORMAT_UNSPECIFIED",
    "TIME_FORMAT_DISABLED",
    "TIME_FORMAT_HOUR_MINUTE",
    "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
}

_FORBIDDEN_XML_DECLARATION = re.compile(r"<!(?:DOCTYPE|ENTITY)\b")


def _validate_no_children(element: ElementTree.Element, path: str) -> None:
    children = list(element)
    if children:
        parse_error(path, f"unknown child element {display_name(children[0].tag)}")


@dataclass
class _TableCellStyleFields:
    background_color: models.Color | None | models.UnsetType = models.UNSET
    border_left: models.TableCellBorder | models.UnsetType = models.UNSET
    border_right: models.TableCellBorder | models.UnsetType = models.UNSET
    border_top: models.TableCellBorder | models.UnsetType = models.UNSET
    border_bottom: models.TableCellBorder | models.UnsetType = models.UNSET
    padding_left: models.Dimension | models.UnsetType = models.UNSET
    padding_right: models.Dimension | models.UnsetType = models.UNSET
    padding_top: models.Dimension | models.UnsetType = models.UNSET
    padding_bottom: models.Dimension | models.UnsetType = models.UNSET
    content_alignment: (
        Literal[
            "CONTENT_ALIGNMENT_UNSPECIFIED",
            "CONTENT_ALIGNMENT_UNSUPPORTED",
            "TOP",
            "MIDDLE",
            "BOTTOM",
        ]
        | models.UnsetType
    ) = models.UNSET

    def has_values(self) -> bool:
        return any(
            value is not models.UNSET
            for value in (
                self.background_color,
                self.border_left,
                self.border_right,
                self.border_top,
                self.border_bottom,
                self.padding_left,
                self.padding_right,
                self.padding_top,
                self.padding_bottom,
                self.content_alignment,
            )
        )


class _Decoder:
    def decode_tag[T: Tag](
        self, element: ElementTree.Element, tag_type: type[T], path: str
    ) -> T:
        recursion_limit = sys.getrecursionlimit()
        try:
            sys.setrecursionlimit(max(recursion_limit, MAX_ELEMENT_DEPTH * 20))
            return XHTMLDecoder().decode_element(element, tag_type)
        except DecodeError as error:
            error_path = path + "".join(f"/{display_name(name)}" for name in error.path)
            if error.attribute_name is not None:
                error_path += f"/@{display_name(error.attribute_name)}"
            message = str(error)
            if message == "required attribute is missing":
                message = "missing required attribute"
            if error.attribute_name is not None:
                if error.attribute_name.startswith(
                    "{"
                ) and not error.attribute_name.startswith(
                    (f"{{{XHTML_NAMESPACE}}}", f"{{{GDOCS_NAMESPACE}}}")
                ):
                    message = (
                        "unsupported namespace in attribute "
                        f"{display_name(error.attribute_name)}"
                    )
                elif message == "unknown attribute":
                    message += f" {display_name(error.attribute_name)}"
            if error.element_name is not None:
                message += f" {display_name(error.element_name)}"
            parse_error(error_path, message, cause=error)
        finally:
            sys.setrecursionlimit(recursion_limit)

    def decode_metadata_text_style(
        self, element: ElementTree.Element, path: str
    ) -> models.TextStyle | models.UnsetType:
        construct_text_style = parse_text_style(element, path)
        validate_whitespace(element, path)
        children = list(element)
        anchor = extract_one_child(children, xhtml_name("a"), path)
        link: models.Link | models.UnsetType = models.UNSET
        if anchor is not None:
            anchor_path = f"{path}/a"
            link = decode_link(anchor, anchor_path)
            validate_whitespace(anchor, anchor_path)
            _validate_no_children(anchor, anchor_path)
        text_style = construct_text_style(link)
        for child in children:
            if child is not anchor:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return text_style

    def decode_document(self, root: tags.HtmlTag) -> models.Document:
        body = cast(tags.BodyTag, cast(list[Node], root.children)[0])
        return models.Document(
            document_id=cast(str, root.document_id),
            title=cast(str, root.title),
            revision_id=root.revision_id,
            suggestions_view_mode=root.suggestions_view_mode,  # type: ignore[arg-type]
            tabs=[
                self.decode_tab(cast(tags.TabTag, child), f"/html/body/g:tab[{index}]")
                for index, child in enumerate(cast(list[Node], body.children), 1)
            ],
        )

    def decode_tab(self, element: tags.TabTag, path: str) -> models.Tab:
        content: models.DocumentTab | models.UnsetType = models.UNSET
        children: list[models.Tab] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.DocumentTabTag):
                content = self.decode_document_tab(child, f"{path}/g:document-tab")
            else:
                assert isinstance(child, tags.ChildTabsTag)
                children = [
                    self.decode_tab(
                        cast(tags.TabTag, tab), f"{path}/g:child-tabs/g:tab[{index}]"
                    )
                    for index, tab in enumerate(cast(list[Node], child.children), 1)
                ]
        return models.Tab(
            tab_id=cast(str, element.tab_id),
            title=cast(str, element.title),
            index=cast(int, element.index),
            nesting_level=cast(int, element.nesting_level),
            parent_tab_id=element.parent_tab_id,
            icon_emoji=element.icon_emoji,
            content=content,
            children=children,
        )

    def decode_document_tab(
        self, element: tags.DocumentTabTag, path: str
    ) -> models.DocumentTab:
        values: dict[str, object] = {
            "body": models.UNSET,
            "headers": models.UNSET,
            "footers": models.UNSET,
            "footnotes": models.UNSET,
            "lists": models.UNSET,
            "document_style": models.UNSET,
            "named_styles": models.UNSET,
        }
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.DocumentStyleTag):
                values["document_style"] = self.decode_document_style(
                    child, f"{path}/g:document-style"
                )
            elif isinstance(child, tags.NamedStylesTag):
                values["named_styles"] = self.decode_named_styles(
                    child, f"{path}/g:named-styles"
                )
            elif isinstance(child, tags.ListDefinitionsTag):
                values["lists"] = self.decode_list_definitions(
                    child, f"{path}/g:list-definitions"
                )
            elif isinstance(child, tags.DocumentBodyTag):
                values["body"] = self.decode_body(child, f"{path}/g:body")
            elif isinstance(
                child, (tags.HeadersTag, tags.FootersTag, tags.FootnotesTag)
            ):
                name, item = {
                    tags.HeadersTag: ("headers", "header"),
                    tags.FootersTag: ("footers", "footer"),
                    tags.FootnotesTag: ("footnotes", "footnote"),
                }[type(child)]
                values[name] = self.decode_segments(child, item, f"{path}/g:{name}")
        return models.DocumentTab(**cast(Any, values))

    def decode_document_style(
        self, element: tags.DocumentStyleTag, path: str
    ) -> models.DocumentStyle:
        values = {
            name: getattr(element, name)
            for name in tags.DocumentStyleTag.fields()
            if name != "children"
        }
        background_color: models.Color | None | models.UnsetType = models.UNSET
        children = cast(list[Node], element.children)
        if children:
            background = cast(tags.BackgroundColorTag, children[0])
            background_color = cast(models.Color | None, background.color)
        return construct_model(
            path,
            lambda: models.DocumentStyle(
                background_color=background_color, **cast(Any, values)
            ),
        )

    def _decode_metadata_text_style_tag(
        self, element: tags.NamedStyleTag | tags.ListLevelTag, path: str
    ) -> models.TextStyle | models.UnsetType:
        values = {
            name: getattr(element, name)
            for name in tags.SpanTag.fields()
            if name != "children"
        }
        link: models.Link | models.UnsetType = models.UNSET
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.MetadataAnchorTag):
                link = self._decode_metadata_link(child)
        if all(value is models.UNSET for value in (*values.values(), link)):
            return models.UNSET
        return construct_model(
            path, lambda: models.TextStyle(**cast(Any, values), link=link)
        )

    def _decode_metadata_link(self, anchor: tags.MetadataAnchorTag) -> models.Link:
        if anchor.href is not models.UNSET:
            return models.UrlLink(url=cast(str, anchor.href))
        if anchor.bookmark_id is not models.UNSET:
            return models.BookmarkLink(
                bookmark_id=cast(str, anchor.bookmark_id), tab_id=anchor.tab_id
            )
        if anchor.heading_id is not models.UNSET:
            return models.HeadingLink(
                heading_id=cast(str, anchor.heading_id), tab_id=anchor.tab_id
            )
        return models.TabLink(tab_id=cast(str, anchor.tab_id))

    def decode_named_styles(
        self, element: tags.NamedStylesTag, path: str
    ) -> list[models.NamedStyle]:
        result: list[models.NamedStyle] = []
        for index, child in enumerate(cast(list[Node], element.children), 1):
            style = cast(tags.NamedStyleTag, child)
            child_path = f"{path}/g:named-style[{index}]"
            paragraph_style: models.ParagraphStyle | models.UnsetType = models.UNSET
            for metadata in cast(list[Node], style.children):
                if isinstance(metadata, tags.NamedParagraphStyleTag):
                    paragraph_style = self._decode_paragraph_style_tag(
                        metadata, f"{child_path}/g:paragraph-style"
                    )
            result.append(
                models.NamedStyle(
                    named_style_type=cast(Any, style.named_style_type),
                    text_style=self._decode_metadata_text_style_tag(style, child_path),
                    paragraph_style=paragraph_style,
                )
            )
        return result

    def decode_list_definitions(
        self, element: tags.ListDefinitionsTag, path: str
    ) -> dict[str, models.ListDefinition]:
        result: dict[str, models.ListDefinition] = {}
        for index, child in enumerate(cast(list[Node], element.children), 1):
            definition = cast(tags.ListDefinitionTag, child)
            child_path = f"{path}/g:list-definition[{index}]"
            list_id = cast(str, definition.list_id)
            if list_id in result:
                parse_error(child_path, f"duplicate list key {list_id!r}")
            result[list_id] = models.ListDefinition(
                levels=[
                    self.decode_list_level(cast(tags.ListLevelTag, level), level_path)
                    for level_index, level in enumerate(
                        cast(list[Node], definition.children), 1
                    )
                    for level_path in [f"{child_path}/g:list-level[{level_index}]"]
                ]
            )
        return result

    def decode_list_level(
        self, element: tags.ListLevelTag, path: str
    ) -> models.ListLevel:
        return construct_model(
            path,
            lambda: models.ListLevel(
                glyph_format=cast(str, element.glyph_format),
                glyph_type=element.glyph_type,  # type: ignore[arg-type]
                glyph_symbol=element.glyph_symbol,
                alignment=cast(Any, element.alignment),
                indent_first_line=element.indent_first_line,
                indent_start=element.indent_start,
                start_number=cast(int, element.start_number),
                text_style=self._decode_metadata_text_style_tag(element, path),
            ),
        )

    def decode_body(self, element: tags.DocumentBodyTag, path: str) -> models.Body:
        content: list[models.StructuralElement] = []
        sections = cast(list[Node], element.children)
        if not sections:
            parse_error(path, "body must contain at least one section")
        for index, child in enumerate(sections, 1):
            section = cast(tags.SectionTag, child)
            section_path = f"{path}/section[{index}]"
            section_children = cast(list[Node], section.children)
            style = next(
                item
                for item in section_children
                if isinstance(item, tags.SectionStyleTag)
            )
            content.append(
                models.SectionBreak(
                    style=self.decode_section_style(
                        style, f"{section_path}/g:section-style"
                    )
                )
            )
            content.extend(
                self.decode_structural_sequence(
                    [item for item in section_children if item is not style],
                    section_path,
                )
            )
        return models.Body(content=content)

    def decode_section_style(
        self, element: tags.SectionStyleTag, path: str
    ) -> models.SectionStyle:
        values = {
            name: getattr(element, name)
            for name in tags.SectionStyleTag.fields()
            if name != "children"
        }
        columns: list[models.SectionColumn] | models.UnsetType = models.UNSET
        children = cast(list[Node], element.children)
        if children:
            wrapper = cast(tags.SectionColumnsTag, children[0])
            columns = [
                models.SectionColumn(
                    width=cast(models.Dimension, column.width),
                    padding_end=cast(models.Dimension, column.padding_end),
                )
                for child in cast(list[Node], wrapper.children)
                for column in [cast(tags.SectionColumnTag, child)]
            ]
        return construct_model(
            path,
            lambda: models.SectionStyle(columns=columns, **cast(Any, values)),
        )

    def decode_segments(
        self,
        wrapper: tags.HeadersTag | tags.FootersTag | tags.FootnotesTag,
        item_name: str,
        path: str,
    ) -> dict[str, models.Segment]:
        result: dict[str, models.Segment] = {}
        for index, child in enumerate(cast(list[Node], wrapper.children), 1):
            item = cast(tags.SegmentTag, child)
            item_path = f"{path}/g:{item_name}[{index}]"
            key = cast(str, item.key)
            if key in result:
                parse_error(item_path, f"duplicate segment key {key!r}")
            result[key] = models.Segment(
                segment_id=cast(str, item.segment_id),
                content=self.decode_structural_sequence(
                    cast(list[Node], item.children), item_path
                ),
            )
        return result

    def decode_structural_sequence(
        self,
        elements: list[Node],
        path: str,
        body: bool = False,
    ) -> list[models.StructuralElement]:
        del body
        decoded: list[models.StructuralElement] = []
        counts: dict[str, int] = {}
        for element in elements:
            assert isinstance(element, Tag)
            name = display_name(cast(str, element.tag_name))
            counts[name] = counts.get(name, 0) + 1
            child_path = f"{path}/{name}[{counts[name]}]"
            if isinstance(element, tags.SectionTag):
                parse_error(child_path, "section elements are only valid in a body")
            if isinstance(element, tags.TableOfContentsTag):
                decoded.append(
                    models.TableOfContents(
                        content=self.decode_structural_sequence(
                            cast(list[Node], element.children), child_path
                        )
                    )
                )
                continue
            if not isinstance(element, tags._OpaqueStructuralTag):  # pyright: ignore[reportPrivateUsage]
                parse_error(child_path, "unknown structural element")
            payload = cast(ElementTree.Element, element.payload)
            if isinstance(element, tags.ListTag):
                decoded.extend(self.decode_list(payload, child_path))
            elif isinstance(element, tags.TableTag):
                decoded.append(self.decode_table(payload, child_path))
            else:
                decoded.append(self.decode_paragraph(payload, child_path))
        return decoded

    def optional_allowed(
        self, element: ElementTree.Element, name: str, allowed: set[str], path: str
    ) -> str | models.UnsetType:
        value = element.get(gdocs_name(name))
        return (
            models.UNSET
            if value is None
            else parse_allowed(value, allowed, f"{path}/@g:{name}")
        )

    def optional_boolean(
        self, element: ElementTree.Element, name: str, path: str
    ) -> bool | models.UnsetType:
        value = element.get(gdocs_name(name))
        return (
            models.UNSET if value is None else parse_boolean(value, f"{path}/@g:{name}")
        )

    def optional_integer(
        self, element: ElementTree.Element, name: str, path: str
    ) -> int | models.UnsetType:
        value = element.get(gdocs_name(name))
        return (
            models.UNSET if value is None else parse_integer(value, f"{path}/@g:{name}")
        )

    def optional_point(
        self, element: ElementTree.Element, name: str, path: str
    ) -> models.Dimension | models.UnsetType:
        value = element.get(gdocs_name(name))
        if value is None:
            return models.UNSET
        return models.Dimension(
            magnitude=parse_float(value, f"{path}/@g:{name}"), unit="PT"
        )

    def required_point(
        self, element: ElementTree.Element, name: str, path: str
    ) -> models.Dimension:
        value = required_string(element, gdocs_name(name), path)
        return models.Dimension(
            magnitude=parse_float(value, f"{path}/@g:{name}"), unit="PT"
        )

    def _structural_tag_type(self, name: str) -> type[Tag]:
        return {
            value.tag_name: value
            for value in (
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
                tags.ListTag,
                tags.TableTag,
                tags.TableOfContentsTag,
            )
        }[name]

    def decode_list(
        self, element: ElementTree.Element, path: str
    ) -> list[models.Paragraph]:
        validate_attributes(
            element, {gdocs_name("list-id"), gdocs_name("bullet-preset")}, path
        )
        list_id = element.get(gdocs_name("list-id"))
        raw_preset = element.get(gdocs_name("bullet-preset"))
        preset = (
            None
            if raw_preset is None
            else parse_allowed(raw_preset, _BULLET_PRESETS, f"{path}/@g:bullet-preset")
        )
        validate_whitespace(element, path)
        items = list(element)
        for item in items:
            if item.tag != xhtml_name("li"):
                parse_error(path, f"unknown child element {display_name(item.tag)}")
        if (list_id is None) == (raw_preset is None):
            parse_error(
                path, "exactly one of g:list-id and g:bullet-preset is required"
            )
        if not items:
            parse_error(path, "list must contain at least one item")
        result: list[models.Paragraph] = []
        for index, item in enumerate(items):
            item_path = f"{path}/li[{index + 1}]"
            validate_attributes(item, {gdocs_name("nesting-level")}, item_path)
            raw_level = item.get(gdocs_name("nesting-level"))
            level = (
                0
                if raw_level is None
                else parse_integer(raw_level, f"{item_path}/@g:nesting-level")
            )
            validate_whitespace(item, item_path)
            children = list(item)
            style_element = extract_one_child(
                children, gdocs_name("bullet-style"), item_path
            )
            style = (
                models.UNSET
                if style_element is None
                else self.decode_bullet_style(
                    style_element, f"{item_path}/g:bullet-style"
                )
            )
            paragraph_elements = [
                child for child in children if child.tag in _PARAGRAPH_TAGS
            ]
            unknown = [
                child
                for child in children
                if child is not style_element and child.tag not in _PARAGRAPH_TAGS
            ]
            if unknown:
                parse_error(
                    item_path, f"unknown child element {display_name(unknown[0].tag)}"
                )
            if len(paragraph_elements) != 1:
                parse_error(item_path, "list item must contain exactly one paragraph")
            paragraph = self.decode_paragraph(paragraph_elements[0], item_path + "/*")
            if preset is not None and style_element is not None:
                parse_error(item_path, "bullet style is forbidden in a preset list")
            if level < 0:
                parse_error(item_path, "nesting level must be non-negative")
            paragraph.bullet = (
                models.Bullet(
                    list_id=cast(str, list_id), nesting_level=level, text_style=style
                )
                if preset is None
                else models.BulletPreset(preset=preset, nesting_level=level)  # type: ignore[arg-type]
            )
            result.append(paragraph)
        return result

    def decode_bullet_style(
        self, element: ElementTree.Element, path: str
    ) -> models.TextStyle | models.UnsetType:
        validate_attributes(element, text_style_attributes(), path)
        return self.decode_metadata_text_style(element, path)

    def decode_table(self, element: ElementTree.Element, path: str) -> models.Table:
        validate_attributes(element, {gdocs_name("table-key")}, path)
        table_key = element.get(gdocs_name("table-key"))
        validate_whitespace(element, path)
        children = list(element)
        colgroup = extract_one_child(children, xhtml_name("colgroup"), path)
        columns: list[models.TableColumn] | models.UnsetType = models.UNSET
        if colgroup is not None:
            columns = self.decode_table_columns(colgroup, f"{path}/colgroup")
        tbody = extract_one_child(children, xhtml_name("tbody"), path, required=True)
        assert tbody is not None
        tbody_path = f"{path}/tbody"
        validate_attributes(tbody, set(), tbody_path)
        validate_whitespace(tbody, tbody_path)
        rows: list[models.TableRow] = []
        for index, child in enumerate(tbody):
            if child.tag != xhtml_name("tr"):
                parse_error(
                    tbody_path, f"unknown child element {display_name(child.tag)}"
                )
            rows.append(self.decode_table_row(child, f"{tbody_path}/tr[{index + 1}]"))
        for child in children:
            if child not in (colgroup, tbody):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return models.Table(
            rows=rows,
            column_styles=columns,
            table_key=table_key,
        )

    def decode_table_columns(
        self, element: ElementTree.Element, path: str
    ) -> list[models.TableColumn]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: list[models.TableColumn] = []
        allowed_width_types = {
            "WIDTH_TYPE_UNSPECIFIED",
            "EVENLY_DISTRIBUTED",
            "FIXED_WIDTH",
        }
        for index, child in enumerate(element):
            child_path = f"{path}/col[{index + 1}]"
            if child.tag != xhtml_name("col"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            validate_attributes(
                child, {gdocs_name("width-type"), gdocs_name("width")}, child_path
            )
            width_type = parse_allowed(
                required_string(child, gdocs_name("width-type"), child_path),
                allowed_width_types,
                f"{child_path}/@g:width-type",
            )
            raw_width = child.get(gdocs_name("width"))
            width = (
                models.UNSET
                if raw_width is None
                else models.Dimension(
                    magnitude=parse_float(raw_width, f"{child_path}/@g:width"),
                    unit="PT",
                )
            )
            validate_whitespace(child, child_path)
            _validate_no_children(child, child_path)
            if width_type == "FIXED_WIDTH" and raw_width is None:
                parse_error(child_path, "FIXED_WIDTH column requires width")
            if width_type != "FIXED_WIDTH" and raw_width is not None:
                parse_error(
                    child_path, "width is forbidden unless width type is FIXED_WIDTH"
                )
            result.append(
                construct_model(
                    child_path,
                    lambda: models.TableColumn(width_type=width_type, width=width),  # type: ignore[arg-type]
                )
            )
        return result

    def decode_table_row(
        self, element: ElementTree.Element, path: str
    ) -> models.TableRow:
        validate_attributes(
            element,
            {
                gdocs_name("row-key"),
                gdocs_name("min-height"),
                gdocs_name("prevent-overflow"),
                gdocs_name("is-header"),
            },
            path,
        )
        min_height = self.optional_point(element, "min-height", path)
        prevent_overflow = self.optional_boolean(element, "prevent-overflow", path)
        is_header = self.optional_boolean(element, "is-header", path)
        row_key = element.get(gdocs_name("row-key"))
        validate_whitespace(element, path)
        cells: list[models.TableCell] = []
        for index, child in enumerate(element):
            if child.tag != xhtml_name("td"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            cells.append(self.decode_table_cell(child, f"{path}/td[{index + 1}]"))
        return models.TableRow(
            cells=cells,
            min_height=min_height,
            prevent_overflow=prevent_overflow,
            is_header=is_header,
            row_key=row_key,
        )

    def decode_table_cell(
        self, element: ElementTree.Element, path: str
    ) -> models.TableCell:
        validate_attributes(
            element,
            {gdocs_name("cell-key"), "rowspan", "colspan"},
            path,
        )
        cell_key = element.get(gdocs_name("cell-key"))
        row_span = self.decode_cell_span(element, "rowspan", path)
        column_span = self.decode_cell_span(element, "colspan", path)
        validate_whitespace(element, path)
        children = list(element)
        metadata = extract_one_child(children, gdocs_name("cell-style"), path)
        style_fields = (
            _TableCellStyleFields()
            if metadata is None
            else self.decode_table_cell_style(metadata, f"{path}/g:cell-style")
        )
        content = self.decode_structural_sequence(
            [
                self.decode_tag(
                    child,
                    self._structural_tag_type(child.tag),
                    f"{path}/*[{index}]",
                )
                for index, child in enumerate(
                    (child for child in children if child is not metadata), 1
                )
            ],
            path,
        )
        self.validate_cell_span(element, row_span, "rowspan", path)
        self.validate_cell_span(element, column_span, "colspan", path)
        style: models.TableCellStyle | models.UnsetType = models.UNSET
        if row_span != 1 or column_span != 1 or style_fields.has_values():
            style = construct_model(
                path,
                lambda: models.TableCellStyle(
                    row_span=row_span,
                    column_span=column_span,
                    background_color=style_fields.background_color,
                    border_left=style_fields.border_left,
                    border_right=style_fields.border_right,
                    border_top=style_fields.border_top,
                    border_bottom=style_fields.border_bottom,
                    padding_left=style_fields.padding_left,
                    padding_right=style_fields.padding_right,
                    padding_top=style_fields.padding_top,
                    padding_bottom=style_fields.padding_bottom,
                    content_alignment=style_fields.content_alignment,
                ),
            )
        return models.TableCell(content=content, style=style, cell_key=cell_key)

    def decode_cell_span(
        self, element: ElementTree.Element, name: str, path: str
    ) -> int:
        raw = element.get(name)
        if raw is None:
            return 1
        return parse_integer(raw, f"{path}/@{name}")

    def validate_cell_span(
        self, element: ElementTree.Element, value: int, name: str, path: str
    ) -> None:
        if element.get(name) is not None and value <= 1:
            parse_error(f"{path}/@{name}", "cell span must be greater than 1")

    def decode_table_cell_style(
        self, element: ElementTree.Element, path: str
    ) -> _TableCellStyleFields:
        attribute_names = {
            "content-alignment",
            "padding-left",
            "padding-right",
            "padding-top",
            "padding-bottom",
        }
        validate_attributes(
            element, {gdocs_name(name) for name in attribute_names}, path
        )
        content_alignment = cast(
            "Literal['CONTENT_ALIGNMENT_UNSPECIFIED', 'CONTENT_ALIGNMENT_UNSUPPORTED', 'TOP', 'MIDDLE', 'BOTTOM'] | models.UnsetType",
            self.optional_allowed(
                element,
                "content-alignment",
                {
                    "CONTENT_ALIGNMENT_UNSPECIFIED",
                    "CONTENT_ALIGNMENT_UNSUPPORTED",
                    "TOP",
                    "MIDDLE",
                    "BOTTOM",
                },
                path,
            ),
        )
        padding_left = self.optional_point(element, "padding-left", path)
        padding_right = self.optional_point(element, "padding-right", path)
        padding_top = self.optional_point(element, "padding-top", path)
        padding_bottom = self.optional_point(element, "padding-bottom", path)
        validate_whitespace(element, path)
        children = list(element)
        background = extract_one_child(children, gdocs_name("background-color"), path)
        background_color = (
            models.UNSET
            if background is None
            else self.decode_optional_color(background, f"{path}/g:background-color")
        )
        border_left_element = extract_one_child(
            children, gdocs_name("border-left"), path
        )
        border_left = (
            models.UNSET
            if border_left_element is None
            else self.decode_table_cell_border(
                border_left_element, f"{path}/g:border-left"
            )
        )
        border_right_element = extract_one_child(
            children, gdocs_name("border-right"), path
        )
        border_right = (
            models.UNSET
            if border_right_element is None
            else self.decode_table_cell_border(
                border_right_element, f"{path}/g:border-right"
            )
        )
        border_top_element = extract_one_child(children, gdocs_name("border-top"), path)
        border_top = (
            models.UNSET
            if border_top_element is None
            else self.decode_table_cell_border(
                border_top_element, f"{path}/g:border-top"
            )
        )
        border_bottom_element = extract_one_child(
            children, gdocs_name("border-bottom"), path
        )
        border_bottom = (
            models.UNSET
            if border_bottom_element is None
            else self.decode_table_cell_border(
                border_bottom_element, f"{path}/g:border-bottom"
            )
        )
        known = {gdocs_name("background-color")} | {
            gdocs_name(name)
            for name in ("border-left", "border-right", "border-top", "border-bottom")
        }
        for child in children:
            if child.tag not in known:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return _TableCellStyleFields(
            background_color=background_color,
            border_left=border_left,
            border_right=border_right,
            border_top=border_top,
            border_bottom=border_bottom,
            padding_left=padding_left,
            padding_right=padding_right,
            padding_top=padding_top,
            padding_bottom=padding_bottom,
            content_alignment=content_alignment,
        )

    def decode_table_cell_border(
        self, element: ElementTree.Element, path: str
    ) -> models.TableCellBorder:
        validate_attributes(
            element, {gdocs_name("dash-style"), gdocs_name("width")}, path
        )
        width = self.required_point(element, "width", path)
        dash_style = parse_allowed(
            required_string(element, gdocs_name("dash-style"), path),
            _DASH_STYLES,
            f"{path}/@g:dash-style",
        )
        validate_whitespace(element, path)
        children = list(element)
        color = extract_one_child(children, gdocs_name("color"), path, required=True)
        assert color is not None
        decoded_color = self.decode_optional_color(color, f"{path}/g:color")
        for child in children:
            if child is not color:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return models.TableCellBorder(
            color=decoded_color,
            width=width,
            dash_style=dash_style,  # type: ignore[arg-type]
        )

    def decode_paragraph(
        self, element: ElementTree.Element, path: str
    ) -> models.Paragraph:
        children = list(element)
        declarative_tags = {tags.SpanTag.tag_name, tags.ParagraphStyleTag.tag_name}
        if element.tag == tags.SimpleParagraphTag.tag_name and all(
            child.tag in declarative_tags for child in children
        ):
            paragraph_tag = self.decode_tag(element, tags.SimpleParagraphTag, path)
            paragraph_children = cast(list[Node], paragraph_tag.children)
            style_tag = next(
                (
                    child
                    for child in paragraph_children
                    if isinstance(child, tags.ParagraphStyleTag)
                ),
                None,
            )
            style = (
                models.ParagraphStyle(named_style_type="NORMAL_TEXT")
                if style_tag is None
                else self._decode_paragraph_style_tag(
                    style_tag,
                    f"{path}/g:paragraph-style",
                    owning_named_style="NORMAL_TEXT",
                )
            )
            elements: list[models.ParagraphElement] = []
            for index, child in enumerate(paragraph_children):
                if isinstance(child, tags.SpanTag):
                    elements.append(
                        self._decode_text_run_span(
                            child, models.UNSET, f"{path}/*[{index + 1}]"
                        )
                    )
            return models.Paragraph(elements=elements, style=style)

        validate_attributes(element, set(), path)
        if element.text is not None and element.text.strip():
            parse_error(path, "unexpected text content")
        metadata = extract_one_child(children, gdocs_name("paragraph-style"), path)
        named_style_type = _PARAGRAPH_TAGS[element.tag]
        decoded_style: models.ParagraphStyle | models.UnsetType = models.UNSET
        if metadata is not None:
            metadata_path = f"{path}/g:paragraph-style"
            if metadata.get(gdocs_name("named-style-type")) is not None:
                parse_error(
                    metadata_path,
                    "named style type is owned by the paragraph element",
                )
            decoded_style = self._decode_paragraph_style_tag(
                self.decode_tag(metadata, tags.ParagraphStyleTag, metadata_path),
                metadata_path,
                owning_named_style=named_style_type,
            )
        elif named_style_type is not models.UNSET:
            decoded_style = models.ParagraphStyle(named_style_type=named_style_type)  # type: ignore[arg-type]
        positioned = extract_one_child(children, gdocs_name("positioned-objects"), path)
        positioned_ids: list[str] | models.UnsetType = models.UNSET
        if positioned is not None:
            positioned_ids = self.decode_positioned_objects(
                positioned, f"{path}/g:positioned-objects"
            )
        runs: list[models.ParagraphElement] = []
        for index, child in enumerate(children):
            if child.tail is not None and child.tail.strip():
                parse_error(path, "unexpected text between paragraph elements")
            if child in (metadata, positioned):
                continue
            child_path = f"{path}/*[{index + 1}]"
            runs.append(self.decode_paragraph_element(child, child_path))
        return models.Paragraph(
            elements=runs,
            style=decoded_style,
            positioned_object_ids=positioned_ids,
        )

    def decode_paragraph_element(
        self, element: ElementTree.Element, path: str
    ) -> models.ParagraphElement:
        if element.tag == xhtml_name("a"):
            link = decode_link(element, path)
            if element.text is not None and element.text.strip():
                parse_error(path, "unexpected text in link")
            children = list(element)
            if len(children) != 1:
                parse_error(
                    path, "link target must contain exactly one paragraph element"
                )
            child = children[0]
            if child.tail is not None and child.tail.strip():
                parse_error(path, "unexpected text after linked paragraph element")
            return self.decode_unlinked_paragraph_element(child, link, f"{path}/*[1]")
        return self.decode_unlinked_paragraph_element(element, models.UNSET, path)

    def decode_unlinked_paragraph_element(
        self,
        element: ElementTree.Element,
        link: models.Link | models.UnsetType,
        path: str,
    ) -> models.ParagraphElement:
        if element.tag == xhtml_name("span"):
            return self.decode_text_run(element, link, path)
        if element.tag == gdocs_name("equation"):
            validate_attributes(element, set(), path)
            validate_whitespace(element, path)
            _validate_no_children(element, path)
            if link is not models.UNSET:
                parse_error(path, "equation cannot be a link target")
            return models.Equation()

        fields: set[str]
        if element.tag == gdocs_name("auto-text"):
            fields = {"type"}
        elif element.tag == gdocs_name("column-break"):
            fields = set()
        elif element.tag == xhtml_name("time"):
            fields = {
                "date-id",
                "date-format",
                "display-text",
                "locale",
                "time-format",
                "time-zone-id",
            }
        elif element.tag == gdocs_name("footnote-reference"):
            fields = {"footnote-id", "footnote-number"}
        elif element.tag == xhtml_name("hr"):
            fields = set()
        elif element.tag == gdocs_name("inline-object"):
            fields = {"inline-object-id"}
        elif element.tag == gdocs_name("page-break"):
            fields = set()
        elif element.tag == gdocs_name("person"):
            fields = {"person-id", "email", "name"}
        elif element.tag == gdocs_name("rich-link"):
            fields = {"rich-link-id", "uri", "title", "mime-type"}
        else:
            parse_error(path, f"unknown paragraph element {display_name(element.tag)}")

        allowed = {gdocs_name(name) for name in fields} | text_style_attributes()
        if element.tag == xhtml_name("time"):
            allowed.add("datetime")
        validate_attributes(element, allowed, path)

        construct_text_style = parse_text_style(element, path)

        def finish_text_style() -> models.TextStyle | models.UnsetType:
            validate_whitespace(element, path)
            _validate_no_children(element, path)
            return construct_text_style(link)

        if element.tag == gdocs_name("auto-text"):
            auto_text_type = parse_allowed(
                required_string(element, gdocs_name("type"), path),
                {"TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"},
                f"{path}/@g:type",
            )
            return models.AutoText(
                auto_text_type=auto_text_type,  # type: ignore[arg-type]
                text_style=finish_text_style(),
            )
        if element.tag == gdocs_name("column-break"):
            return models.ColumnBreak(text_style=finish_text_style())
        if element.tag == xhtml_name("time"):
            date_id = required_string(element, gdocs_name("date-id"), path)
            raw_date_format = element.get(gdocs_name("date-format"))
            date_format = (
                models.UNSET
                if raw_date_format is None
                else parse_allowed(
                    raw_date_format, _DATE_FORMATS, f"{path}/@g:date-format"
                )
            )
            display_text = optional_string(element, gdocs_name("display-text"))
            locale = optional_string(element, gdocs_name("locale"))
            raw_time_format = element.get(gdocs_name("time-format"))
            time_format = (
                models.UNSET
                if raw_time_format is None
                else parse_allowed(
                    raw_time_format, _TIME_FORMATS, f"{path}/@g:time-format"
                )
            )
            time_zone_id = optional_string(element, gdocs_name("time-zone-id"))
            timestamp = optional_string(element, "datetime")
            return models.DateElement(
                date_id=date_id,
                date_format=date_format,  # type: ignore[arg-type]
                display_text=display_text,
                locale=locale,
                time_format=time_format,  # type: ignore[arg-type]
                time_zone_id=time_zone_id,
                timestamp=timestamp,
                text_style=finish_text_style(),
            )
        if element.tag == gdocs_name("footnote-reference"):
            footnote_id = required_string(element, gdocs_name("footnote-id"), path)
            footnote_number = required_string(
                element, gdocs_name("footnote-number"), path
            )
            return models.FootnoteReference(
                footnote_id=footnote_id,
                footnote_number=footnote_number,
                text_style=finish_text_style(),
            )
        if element.tag == xhtml_name("hr"):
            return models.HorizontalRule(text_style=finish_text_style())
        if element.tag == gdocs_name("inline-object"):
            inline_object_id = required_string(
                element, gdocs_name("inline-object-id"), path
            )
            return models.InlineObjectReference(
                inline_object_id=inline_object_id,
                text_style=finish_text_style(),
            )
        if element.tag == gdocs_name("page-break"):
            return models.PageBreak(text_style=finish_text_style())
        if element.tag == gdocs_name("person"):
            person_id = required_string(element, gdocs_name("person-id"), path)
            email = optional_string(element, gdocs_name("email"))
            name = optional_string(element, gdocs_name("name"))
            return models.PersonReference(
                person_id=person_id,
                email=email,
                name=name,
                text_style=finish_text_style(),
            )
        assert element.tag == gdocs_name("rich-link")
        rich_link_id = required_string(element, gdocs_name("rich-link-id"), path)
        uri = required_string(element, gdocs_name("uri"), path)
        title = optional_string(element, gdocs_name("title"))
        mime_type = optional_string(element, gdocs_name("mime-type"))
        return models.RichLink(
            rich_link_id=rich_link_id,
            uri=uri,
            title=title,
            mime_type=mime_type,
            text_style=finish_text_style(),
        )

    def decode_positioned_objects(
        self, element: ElementTree.Element, path: str
    ) -> list[str]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: list[str] = []
        for index, child in enumerate(element):
            child_path = f"{path}/g:positioned-object[{index + 1}]"
            if child.tag != gdocs_name("positioned-object"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            validate_attributes(child, {gdocs_name("id")}, child_path)
            object_id = required_string(child, gdocs_name("id"), child_path)
            validate_whitespace(child, child_path)
            _validate_no_children(child, child_path)
            result.append(object_id)
        return result

    def _decode_paragraph_style_tag(
        self,
        style_tag: tags.ParagraphStyleTag,
        path: str,
        *,
        owning_named_style: object = models.UNSET,
    ) -> models.ParagraphStyle:
        values = {
            name: getattr(style_tag, name)
            for name in type(style_tag).fields()
            if name != "children"
        }
        if not isinstance(style_tag, tags.NamedParagraphStyleTag):
            values["named_style_type"] = owning_named_style
        border_fields: dict[type[Node], str] = {
            tags.BorderBetweenTag: "border_between",
            tags.BorderTopTag: "border_top",
            tags.BorderBottomTag: "border_bottom",
            tags.BorderLeftTag: "border_left",
            tags.BorderRightTag: "border_right",
        }
        children = cast(list[Node], style_tag.children)
        for child in children:
            field_name = border_fields.get(type(child))
            if field_name is not None:
                assert isinstance(child, tags.ParagraphBorderTag)
                values[field_name] = self._decode_paragraph_border_tag(
                    child, f"{path}/{display_name(child.tag_name or '')}"
                )
            elif isinstance(child, tags.ShadingColorTag):
                values["shading_color"] = cast(models.Color | None, child.color)
            elif isinstance(child, tags.TabStopsTag):
                values["tab_stops"] = [
                    models.TabStop(
                        alignment=cast(Any, stop.alignment),
                        offset=cast(models.Dimension, stop.offset),
                    )
                    for stop in cast(list[tags.TabStopTag], child.children)
                ]

        return construct_model(
            path,
            lambda: models.ParagraphStyle(**cast(Any, values)),
        )

    def _decode_paragraph_border_tag(
        self, border_tag: tags.ParagraphBorderTag, path: str
    ) -> models.ParagraphBorder:
        children = cast(list[Node], border_tag.children)
        color_tag = cast(tags.ColorTag, children[0])
        return construct_model(
            path,
            lambda: models.ParagraphBorder(
                color=cast(models.Color | None, color_tag.color),
                width=cast(models.Dimension, border_tag.width),
                padding=cast(models.Dimension, border_tag.padding),
                dash_style=cast(Any, border_tag.dash_style),
            ),
        )

    def decode_optional_color(
        self, element: ElementTree.Element, path: str
    ) -> models.Color | None:
        names = {
            name: gdocs_name(name) for name in ("red", "green", "blue", "transparent")
        }
        validate_attributes(element, set(names.values()), path)
        transparent = element.get(names["transparent"])
        transparent_value = (
            models.UNSET
            if transparent is None
            else parse_boolean(transparent, f"{path}/@g:transparent")
        )
        components = [element.get(names[name]) for name in ("red", "green", "blue")]
        parsed_components = [
            None if value is None else parse_float(value, f"{path}/@g:{name}")
            for name, value in zip(("red", "green", "blue"), components, strict=True)
        ]
        validate_whitespace(element, path)
        _validate_no_children(element, path)
        if transparent is not None:
            if transparent_value is not True or any(
                value is not None for value in components
            ):
                parse_error(path, "transparent color cannot include RGB components")
            return None
        if not all(value is not None for value in components):
            parse_error(path, "opaque color requires red, green, and blue")
        red, green, blue = cast("list[float]", parsed_components)
        try:
            return models.Color(red=red, green=green, blue=blue)
        except ValueError as error:
            parse_error(path, str(error), cause=error)

    def decode_linked_text_run(
        self, anchor: ElementTree.Element, path: str
    ) -> models.TextRun:
        link = decode_link(anchor, path)
        if anchor.text is not None and anchor.text.strip():
            parse_error(path, "unexpected text in link")
        children = list(anchor)
        if len(children) != 1 or children[0].tag != xhtml_name("span"):
            parse_error(path, "link target must contain exactly one span")
        span = children[0]
        if span.tail is not None and span.tail.strip():
            parse_error(path, "unexpected text after linked span")
        return self.decode_text_run(span, link, f"{path}/span")

    def decode_text_run(
        self, span: ElementTree.Element, link: models.Link | models.UnsetType, path: str
    ) -> models.TextRun:
        return self._decode_text_run_span(
            self.decode_tag(span, tags.SpanTag, path), link, path
        )

    def _decode_text_run_span(
        self, span_tag: tags.SpanTag, link: models.Link | models.UnsetType, path: str
    ) -> models.TextRun:
        style_values = {
            name: getattr(span_tag, name)
            for name in tags.SpanTag.fields()
            if name != "children"
        }
        text_style: models.TextStyle | models.UnsetType = models.UNSET
        if (
            any(value is not models.UNSET for value in style_values.values())
            or link is not models.UNSET
        ):
            text_style = construct_model(
                path,
                lambda: models.TextStyle(**cast(Any, style_values), link=link),
            )

        content = ""
        children = cast(list[Node], span_tag.children)
        for child in children:
            if isinstance(child, Text):
                content += child.value
            else:
                assert isinstance(child, tags.BreakTag)
                content += "\n"
        return models.TextRun(content=content, text_style=text_style)


def _preflight_xml(payload: str) -> None:
    if _FORBIDDEN_XML_DECLARATION.search(payload) is not None:
        raise XHTMLParseError("/document: DTD and entity declarations are forbidden")
    parser = expat.ParserCreate()
    depth = 0

    def reject_declaration(*_args: object) -> Never:
        raise XHTMLParseError("/document: DTD and entity declarations are forbidden")

    def reject_external_entity(
        _context: str,
        _base: str | None,
        _system_id: str | None,
        _public_id: str | None,
    ) -> int:
        reject_declaration()

    def start_element(_name: str, _attributes: dict[str, str]) -> None:
        nonlocal depth
        depth += 1
        if depth > MAX_ELEMENT_DEPTH:
            raise XHTMLParseError(
                f"/document: XML element depth exceeds {MAX_ELEMENT_DEPTH}"
            )

    def end_element(_name: str) -> None:
        nonlocal depth
        depth -= 1

    parser.StartDoctypeDeclHandler = reject_declaration
    parser.EntityDeclHandler = reject_declaration
    parser.UnparsedEntityDeclHandler = reject_declaration
    parser.ExternalEntityRefHandler = reject_external_entity
    parser.StartElementHandler = start_element
    parser.EndElementHandler = end_element
    try:
        parser.Parse(payload, True)
    except XHTMLParseError:
        raise
    except (expat.ExpatError, RecursionError, UnicodeEncodeError) as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error


def deserialize_document(xhtml: str) -> models.Document:
    if len(xhtml) > MAX_XHTML_CHARACTERS:
        raise XHTMLParseError(
            f"/document: input exceeds {MAX_XHTML_CHARACTERS} characters"
        )
    if not xhtml.startswith(XML_DECLARATION):
        raise XHTMLParseError(
            "/document: required XML declaration is missing or invalid"
        )
    payload = xhtml[len(XML_DECLARATION) :].lstrip()
    _preflight_xml(payload)
    try:
        root = ElementTree.fromstring(payload)
        if root.tag != xhtml_name("html") and (
            root.tag == "html" or root.tag.endswith("}html")
        ):
            raise XHTMLParseError("/html: unsupported XHTML namespace")
        decoder = _Decoder()
        return decoder.decode_document(decoder.decode_tag(root, tags.HtmlTag, "/html"))
    except XHTMLParseError:
        raise
    except (ElementTree.ParseError, RecursionError) as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error
