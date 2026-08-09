import re
from collections.abc import Callable
from typing import Any, Never, cast
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
    display_name,
    parse_error,
    xhtml_name,
)
from .nodes import (
    DecodeError,
    Node,
    SourceLocation,
    SourceMap,
    SourcePosition,
    Tag,
    TagDecoder,
    Text,
)

_FORBIDDEN_XML_DECLARATION = re.compile(r"<!(?:DOCTYPE|ENTITY)\b")


def _decode_tag[T: Tag](
    element: ElementTree.Element, tag_type: type[T], decoder: TagDecoder
) -> T:
    try:
        with decoder.at(element.tag):
            return decoder.decode_element(element, tag_type)
    except DecodeError as error:
        location = SourceLocation(error.path, error.position)
        suffix = ""
        if error.attribute_name is not None:
            suffix = f"/@{display_name(error.attribute_name)}"
        message = str(error)
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
        parse_error(location.format(suffix), message, cause=error)


class _DocumentDecoder:
    def __init__(self, source_map: SourceMap) -> None:
        self.source_map = source_map

    def source_location(self, element: Tag) -> str:
        return str(self.source_map.location_for(element))

    def construct_model[ModelT](
        self,
        element: Tag,
        model_type: Callable[..., ModelT],
        /,
        **values: object,
    ) -> ModelT:
        try:
            return model_type(**values)
        except ValueError as error:
            parse_error(self.source_location(element), str(error), cause=error)

    def decode_document(self, root: tags.HtmlTag) -> models.Document:
        body = cast(tags.BodyTag, cast(list[Node], root.children)[0])
        return models.Document(
            document_id=cast(str, root.document_id),
            title=cast(str, root.title),
            revision_id=root.revision_id,
            suggestions_view_mode=root.suggestions_view_mode,  # type: ignore[arg-type]
            tabs=[
                self.decode_tab(cast(tags.TabTag, child))
                for child in cast(list[Node], body.children)
            ],
        )

    def decode_tab(self, element: tags.TabTag) -> models.Tab:
        content: models.DocumentTab | models.UnsetType = models.UNSET
        children: list[models.Tab] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.DocumentTabTag):
                content = self.decode_document_tab(child)
            else:
                child_tabs = cast(tags.ChildTabsTag, child)
                children = [
                    self.decode_tab(cast(tags.TabTag, tab))
                    for tab in cast(list[Node], child_tabs.children)
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

    def decode_document_tab(self, element: tags.DocumentTabTag) -> models.DocumentTab:
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
                values["document_style"] = self.decode_document_style(child)
            elif isinstance(child, tags.NamedStylesTag):
                values["named_styles"] = self.decode_named_styles(child)
            elif isinstance(child, tags.ListDefinitionsTag):
                values["lists"] = self.decode_list_definitions(child)
            elif isinstance(child, tags.DocumentBodyTag):
                values["body"] = self.decode_body(child)
            elif isinstance(
                child, (tags.HeadersTag, tags.FootersTag, tags.FootnotesTag)
            ):
                name = {
                    tags.HeadersTag: "headers",
                    tags.FootersTag: "footers",
                    tags.FootnotesTag: "footnotes",
                }[type(child)]
                values[name] = self.decode_segments(child)
        return models.DocumentTab(**cast(Any, values))

    def decode_document_style(
        self, element: tags.DocumentStyleTag
    ) -> models.DocumentStyle:
        values = element.attribute_values
        background_color: models.Color | None | models.UnsetType = models.UNSET
        children = cast(list[Node], element.children)
        if children:
            background = cast(tags.BackgroundColorTag, children[0])
            background_color = cast(models.Color | None, background.color)
        return self.construct_model(
            element,
            models.DocumentStyle,
            background_color=background_color,
            **cast(Any, values),
        )

    def _decode_metadata_text_style_tag(
        self,
        element: tags.NamedStyleTag | tags.ListLevelTag | tags.BulletStyleTag,
    ) -> models.TextStyle | models.UnsetType:
        values = {
            name: getattr(element, name) for name in tags.SpanTag.attribute_fields()
        }
        link: models.Link | models.UnsetType = models.UNSET
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.MetadataAnchorTag):
                link = self._decode_metadata_link(child)
        if all(value is models.UNSET for value in (*values.values(), link)):
            return models.UNSET
        return self.construct_model(
            element, models.TextStyle, **cast(Any, values), link=link
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
        self, element: tags.NamedStylesTag
    ) -> list[models.NamedStyle]:
        result: list[models.NamedStyle] = []
        for child in cast(list[Node], element.children):
            style = cast(tags.NamedStyleTag, child)
            paragraph_style: models.ParagraphStyle | models.UnsetType = models.UNSET
            for metadata in cast(list[Node], style.children):
                if isinstance(metadata, tags.NamedParagraphStyleTag):
                    paragraph_style = self._decode_paragraph_style_tag(metadata)
            result.append(
                models.NamedStyle(
                    named_style_type=cast(Any, style.named_style_type),
                    text_style=self._decode_metadata_text_style_tag(style),
                    paragraph_style=paragraph_style,
                )
            )
        return result

    def decode_list_definitions(
        self, element: tags.ListDefinitionsTag
    ) -> dict[str, models.ListDefinition]:
        result: dict[str, models.ListDefinition] = {}
        for child in cast(list[Node], element.children):
            definition = cast(tags.ListDefinitionTag, child)
            list_id = cast(str, definition.list_id)
            result[list_id] = models.ListDefinition(
                levels=[
                    self.decode_list_level(cast(tags.ListLevelTag, level))
                    for level in cast(list[Node], definition.children)
                ]
            )
        return result

    def decode_list_level(self, element: tags.ListLevelTag) -> models.ListLevel:
        return self.construct_model(
            element,
            models.ListLevel,
            glyph_format=cast(str, element.glyph_format),
            glyph_type=element.glyph_type,
            glyph_symbol=element.glyph_symbol,
            alignment=element.alignment,
            indent_first_line=element.indent_first_line,
            indent_start=element.indent_start,
            start_number=cast(int, element.start_number),
            text_style=self._decode_metadata_text_style_tag(element),
        )

    def decode_body(self, element: tags.DocumentBodyTag) -> models.Body:
        content: list[models.StructuralElement] = []
        sections = cast(list[tags.SectionTag], element.children)
        for section in sections:
            section_children = cast(list[Node], section.children)
            style = next(
                item
                for item in section_children
                if isinstance(item, tags.SectionStyleTag)
            )
            content.append(models.SectionBreak(style=self.decode_section_style(style)))
            content.extend(
                self.decode_structural_sequence(
                    [item for item in section_children if item is not style]
                )
            )
        return models.Body(content=content)

    def decode_section_style(
        self, element: tags.SectionStyleTag
    ) -> models.SectionStyle:
        values = element.attribute_values
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
        return self.construct_model(
            element, models.SectionStyle, columns=columns, **cast(Any, values)
        )

    def decode_segments(
        self,
        wrapper: tags.HeadersTag | tags.FootersTag | tags.FootnotesTag,
    ) -> dict[str, models.Segment]:
        result: dict[str, models.Segment] = {}
        for child in cast(list[Node], wrapper.children):
            item = cast(tags.SegmentTag, child)
            key = cast(str, item.key)
            result[key] = models.Segment(
                segment_id=cast(str, item.segment_id),
                content=self.decode_structural_sequence(
                    cast(list[Node], item.children)
                ),
            )
        return result

    def decode_structural_sequence(
        self, elements: list[Node]
    ) -> list[models.StructuralElement]:
        decoded: list[models.StructuralElement] = []
        for item in elements:
            element = cast(Tag, item)
            if isinstance(element, tags.TableOfContentsTag):
                decoded.append(
                    models.TableOfContents(
                        content=self.decode_structural_sequence(
                            cast(list[Node], element.children)
                        )
                    )
                )
                continue
            if isinstance(element, tags.ParagraphVocabularyTag):
                decoded.append(self.decode_paragraph(element))
                continue
            if isinstance(element, tags.ListTag):
                decoded.extend(self.decode_list(element))
                continue
            decoded.append(self.decode_table(cast(tags.TableTag, element)))
        return decoded

    def decode_list(self, element: tags.ListTag) -> list[models.Paragraph]:
        list_id = element.list_id
        preset = element.bullet_preset
        result: list[models.Paragraph] = []
        for child in cast(list[Node], element.children):
            item = cast(tags.ListItemTag, child)
            style: models.TextStyle | models.UnsetType = models.UNSET
            paragraph_tag: tags.ParagraphVocabularyTag | None = None
            for item_child in cast(list[Node], item.children):
                if isinstance(item_child, tags.BulletStyleTag):
                    if preset is not models.UNSET:
                        parse_error(
                            self.source_location(item_child),
                            "bullet style is forbidden in a preset list",
                        )
                    style = self._decode_metadata_text_style_tag(item_child)
                else:
                    paragraph_tag = cast(tags.ParagraphVocabularyTag, item_child)
            paragraph = self.decode_paragraph(
                cast(tags.ParagraphVocabularyTag, paragraph_tag)
            )
            paragraph.bullet = (
                models.Bullet(
                    list_id=cast(str, list_id),
                    nesting_level=cast(int, item.nesting_level),
                    text_style=style,
                )
                if preset is models.UNSET
                else models.BulletPreset(
                    preset=cast(Any, preset),
                    nesting_level=cast(int, item.nesting_level),
                )
            )
            result.append(paragraph)
        return result

    def decode_table(self, element: tags.TableTag) -> models.Table:
        columns: list[models.TableColumn] | models.UnsetType = models.UNSET
        rows: list[models.TableRow] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.TableColgroupTag):
                columns = [
                    self.construct_model(
                        column,
                        models.TableColumn,
                        width_type=column.width_type,
                        width=column.width,
                    )
                    for column in cast(list[tags.TableColumnTag], child.children)
                ]
            else:
                body = cast(tags.TableBodyTag, child)
                rows = [
                    self.decode_table_row(row)
                    for row in cast(list[tags.TableRowTag], body.children)
                ]
        return models.Table(
            rows=rows,
            column_styles=columns,
            table_key=(
                None
                if element.table_key is models.UNSET
                else cast(str, element.table_key)
            ),
        )

    def decode_table_row(self, element: tags.TableRowTag) -> models.TableRow:
        return models.TableRow(
            cells=[
                self.decode_table_cell(cell)
                for cell in cast(list[tags.TableCellTag], element.children)
            ],
            min_height=element.min_height,
            prevent_overflow=element.prevent_overflow,
            is_header=element.is_header,
            row_key=(
                None if element.row_key is models.UNSET else cast(str, element.row_key)
            ),
        )

    def decode_table_cell(self, element: tags.TableCellTag) -> models.TableCell:
        row_span = (
            1 if element.row_span is models.UNSET else cast(int, element.row_span)
        )
        column_span = (
            1 if element.column_span is models.UNSET else cast(int, element.column_span)
        )
        style_tag: tags.TableCellStyleTag | None = None
        content_tags: list[Node] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.TableCellStyleTag):
                style_tag = child
            else:
                content_tags.append(child)
        style: models.TableCellStyle | models.UnsetType = models.UNSET
        values = {} if style_tag is None else self.decode_table_cell_style(style_tag)
        if (
            row_span != 1
            or column_span != 1
            or any(value is not models.UNSET for value in values.values())
        ):
            style = self.construct_model(
                element,
                models.TableCellStyle,
                row_span=row_span,
                column_span=column_span,
                **cast(Any, values),
            )
        return models.TableCell(
            content=self.decode_structural_sequence(content_tags),
            style=style,
            cell_key=(
                None
                if element.cell_key is models.UNSET
                else cast(str, element.cell_key)
            ),
        )

    def decode_table_cell_style(
        self, element: tags.TableCellStyleTag
    ) -> dict[str, object]:
        values = element.attribute_values
        border_fields: dict[type[Node], str] = {
            tags.TableCellBorderLeftTag: "border_left",
            tags.TableCellBorderRightTag: "border_right",
            tags.TableCellBorderTopTag: "border_top",
            tags.TableCellBorderBottomTag: "border_bottom",
        }
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.TableCellBackgroundColorTag):
                values["background_color"] = child.color
                continue
            border = cast(tags.TableCellBorderTag, child)
            color = cast(tags.ColorTag, cast(list[Node], border.children)[0]).color
            values[border_fields[type(border)]] = self.construct_model(
                border,
                models.TableCellBorder,
                color=cast(models.Color | None, color),
                width=border.width,
                dash_style=border.dash_style,
            )
        return values

    def decode_paragraph(
        self, element: tags.ParagraphVocabularyTag
    ) -> models.Paragraph:
        named_style_types: dict[type[tags.ParagraphVocabularyTag], object] = {
            tags.GenericParagraphTag: models.UNSET,
            tags.UnspecifiedParagraphTag: "NAMED_STYLE_TYPE_UNSPECIFIED",
            tags.ParagraphTag: "NORMAL_TEXT",
            tags.TitleTag: "TITLE",
            tags.SubtitleTag: "SUBTITLE",
            tags.Heading1Tag: "HEADING_1",
            tags.Heading2Tag: "HEADING_2",
            tags.Heading3Tag: "HEADING_3",
            tags.Heading4Tag: "HEADING_4",
            tags.Heading5Tag: "HEADING_5",
            tags.Heading6Tag: "HEADING_6",
        }
        named_style_type = named_style_types[type(element)]
        style: models.ParagraphStyle | models.UnsetType = models.UNSET
        positioned_ids: list[str] | models.UnsetType = models.UNSET
        paragraph_elements: list[models.ParagraphElement] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.ParagraphStyleTag):
                if child.owned_named_style_type is not models.UNSET:
                    parse_error(
                        self.source_location(child),
                        "named style type is owned by the paragraph element",
                    )
                style = self._decode_paragraph_style_tag(
                    child, owning_named_style=named_style_type
                )
            elif isinstance(child, tags.PositionedObjectsTag):
                positioned_ids = [
                    cast(str, positioned.object_id)
                    for positioned in cast(
                        list[tags.PositionedObjectTag], child.children
                    )
                ]
            else:
                paragraph_elements.append(
                    self.decode_paragraph_element(cast(Tag, child))
                )
        if paragraph_elements and isinstance(paragraph_elements[-1], models.TextRun):
            paragraph_elements[-1].content += "\n"
        else:
            paragraph_elements.append(models.TextRun(content="\n"))
        if style is models.UNSET and named_style_type is not models.UNSET:
            style = models.ParagraphStyle(named_style_type=cast(Any, named_style_type))
        return models.Paragraph(
            elements=paragraph_elements,
            style=style,
            positioned_object_ids=positioned_ids,
        )

    def decode_paragraph_element(self, element: Tag) -> models.ParagraphElement:
        link: models.Link | models.UnsetType = models.UNSET
        if isinstance(element, tags.ContentAnchorTag):
            link = self._decode_metadata_link(element)
            element = cast(Tag, cast(list[Node], element.children)[0])
        if isinstance(element, tags.SpanTag):
            return self._decode_text_run_span(element, link)
        if isinstance(element, tags.EquationTag):
            return models.Equation()

        element = cast(tags.StyledParagraphElementTag, element)
        style_values = {
            name: getattr(element, name)
            for name in tags.StyledParagraphElementTag.attribute_fields()
        }
        text_style: models.TextStyle | models.UnsetType = models.UNSET
        if any(value is not models.UNSET for value in (*style_values.values(), link)):
            text_style = self.construct_model(
                element, models.TextStyle, **cast(Any, style_values), link=link
            )
        if isinstance(element, tags.AutoTextTag):
            return models.AutoText(
                auto_text_type=cast(Any, element.auto_text_type), text_style=text_style
            )
        if isinstance(element, tags.ColumnBreakTag):
            return models.ColumnBreak(text_style=text_style)
        if isinstance(element, tags.DateElementTag):
            return models.DateElement(
                date_id=cast(str, element.date_id),
                date_format=cast(Any, element.date_format),
                display_text=element.display_text,
                locale=element.locale,
                time_format=cast(Any, element.time_format),
                time_zone_id=element.time_zone_id,
                timestamp=element.timestamp,
                text_style=text_style,
            )
        if isinstance(element, tags.FootnoteReferenceTag):
            return models.FootnoteReference(
                footnote_id=cast(str, element.footnote_id),
                footnote_number=cast(str, element.footnote_number),
                text_style=text_style,
            )
        if isinstance(element, tags.HorizontalRuleTag):
            return models.HorizontalRule(text_style=text_style)
        if isinstance(element, tags.InlineObjectReferenceTag):
            return models.InlineObjectReference(
                inline_object_id=cast(str, element.inline_object_id),
                text_style=text_style,
            )
        if isinstance(element, tags.PageBreakTag):
            return models.PageBreak(text_style=text_style)
        if isinstance(element, tags.PersonReferenceTag):
            return models.PersonReference(
                person_id=cast(str, element.person_id),
                email=element.email,
                name=element.name,
                text_style=text_style,
            )
        rich_link = cast(tags.RichLinkTag, element)
        return models.RichLink(
            rich_link_id=cast(str, rich_link.rich_link_id),
            uri=cast(str, rich_link.uri),
            title=rich_link.title,
            mime_type=rich_link.mime_type,
            text_style=text_style,
        )

    def _decode_paragraph_style_tag(
        self,
        style_tag: tags.ParagraphStyleTag,
        *,
        owning_named_style: object = models.UNSET,
    ) -> models.ParagraphStyle:
        values = style_tag.attribute_values
        values.pop("owned_named_style_type", None)
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
                border = cast(tags.ParagraphBorderTag, child)
                values[field_name] = self._decode_paragraph_border_tag(border)
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

        return self.construct_model(
            style_tag, models.ParagraphStyle, **cast(Any, values)
        )

    def _decode_paragraph_border_tag(
        self, border_tag: tags.ParagraphBorderTag
    ) -> models.ParagraphBorder:
        children = cast(list[Node], border_tag.children)
        color_tag = cast(tags.ColorTag, children[0])
        return self.construct_model(
            border_tag,
            models.ParagraphBorder,
            color=cast(models.Color | None, color_tag.color),
            width=border_tag.width,
            padding=border_tag.padding,
            dash_style=border_tag.dash_style,
        )

    def _decode_text_run_span(
        self, span_tag: tags.SpanTag, link: models.Link | models.UnsetType
    ) -> models.TextRun:
        style_values = span_tag.attribute_values
        text_style: models.TextStyle | models.UnsetType = models.UNSET
        if (
            any(value is not models.UNSET for value in style_values.values())
            or link is not models.UNSET
        ):
            text_style = self.construct_model(
                span_tag, models.TextStyle, **cast(Any, style_values), link=link
            )

        content = ""
        children = cast(list[Node], span_tag.children)
        for child in children:
            if isinstance(child, Text):
                content += child.value
            elif isinstance(child, tags.BreakTag):
                content += "\n"
            elif isinstance(child, tags.VerticalTabTag):
                content += "\v"
            else:
                content += "\f"
        return models.TextRun(content=content, text_style=text_style)


def _preflight_xml(payload: str) -> list[SourcePosition]:
    """Validate the original XML source and locate its elements.

    Parse the complete input with Expat before ElementTree decoding, rejecting DTD
    and entity declarations, external entity references, malformed XML, and element
    nesting beyond ``MAX_ELEMENT_DEPTH``. Return the one-based line and column of
    every start element in document order; ``nodes.TagDecoder`` consumes these
    positions
    in the same preorder to build its tag source map.
    """
    if _FORBIDDEN_XML_DECLARATION.search(payload) is not None:
        raise XHTMLParseError("/document: DTD and entity declarations are forbidden")
    parser = expat.ParserCreate()
    depth = 0
    positions: list[SourcePosition] = []

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
        positions.append(
            SourcePosition(
                line=parser.CurrentLineNumber,
                column=parser.CurrentColumnNumber + 1,
            )
        )
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
    return positions


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
    source_positions = _preflight_xml(xhtml)
    try:
        root = ElementTree.fromstring(payload)
        if root.tag != xhtml_name("html") and (
            root.tag == "html" or root.tag.endswith("}html")
        ):
            raise XHTMLParseError("/html: unsupported XHTML namespace")
        tag_decoder = TagDecoder(source_positions)
        html = _decode_tag(root, tags.HtmlTag, tag_decoder)
        return _DocumentDecoder(tag_decoder.source_map).decode_document(html)
    except XHTMLParseError:
        raise
    except (ElementTree.ParseError, RecursionError) as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error
