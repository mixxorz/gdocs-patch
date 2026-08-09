import re
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
    construct_model,
    display_name,
    parse_error,
    xhtml_name,
)
from .nodes import DecodeError, Node, Tag, Text
from .nodes import Decoder as XHTMLDecoder

_FORBIDDEN_XML_DECLARATION = re.compile(r"<!(?:DOCTYPE|ENTITY)\b")


def _decode_tag[T: Tag](
    element: ElementTree.Element, tag_type: type[T], path: str
) -> T:
    try:
        return XHTMLDecoder().decode_element(element, tag_type)
    except DecodeError as error:
        error_path = path + "".join(f"/{display_name(name)}" for name in error.path)
        if error.attribute_name is not None:
            error_path += f"/@{display_name(error.attribute_name)}"
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
        parse_error(error_path, message, cause=error)


class _Decoder:
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
                child_tabs = cast(tags.ChildTabsTag, child)
                children = [
                    self.decode_tab(
                        cast(tags.TabTag, tab), f"{path}/g:child-tabs/g:tab[{index}]"
                    )
                    for index, tab in enumerate(
                        cast(list[Node], child_tabs.children), 1
                    )
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
            for name in tags.DocumentStyleTag.attribute_fields()
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
        self,
        element: tags.NamedStyleTag | tags.ListLevelTag | tags.BulletStyleTag,
        path: str,
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
        sections = cast(list[tags.SectionTag], element.children)
        for index, section in enumerate(sections, 1):
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
            for name in tags.SectionStyleTag.attribute_fields()
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
        for item in elements:
            element = cast(Tag, item)
            name = display_name(cast(str, element.tag_name))
            counts[name] = counts.get(name, 0) + 1
            child_path = f"{path}/{name}[{counts[name]}]"
            if isinstance(element, tags.TableOfContentsTag):
                decoded.append(
                    models.TableOfContents(
                        content=self.decode_structural_sequence(
                            cast(list[Node], element.children), child_path
                        )
                    )
                )
                continue
            if isinstance(element, tags.ParagraphVocabularyTag):
                decoded.append(self.decode_paragraph(element, child_path))
                continue
            if isinstance(element, tags.ListTag):
                decoded.extend(self.decode_list(element, child_path))
                continue
            decoded.append(self.decode_table(cast(tags.TableTag, element), child_path))
        return decoded

    def decode_list(self, element: tags.ListTag, path: str) -> list[models.Paragraph]:
        list_id = element.list_id
        preset = element.bullet_preset
        result: list[models.Paragraph] = []
        for index, child in enumerate(cast(list[Node], element.children), 1):
            item = cast(tags.ListItemTag, child)
            item_path = f"{path}/li[{index}]"
            style: models.TextStyle | models.UnsetType = models.UNSET
            paragraph_tag: tags.ParagraphVocabularyTag | None = None
            for item_child in cast(list[Node], item.children):
                if isinstance(item_child, tags.BulletStyleTag):
                    if preset is not models.UNSET:
                        parse_error(
                            item_path, "bullet style is forbidden in a preset list"
                        )
                    style = self._decode_metadata_text_style_tag(
                        item_child, f"{item_path}/g:bullet-style"
                    )
                else:
                    paragraph_tag = cast(tags.ParagraphVocabularyTag, item_child)
            paragraph = self.decode_paragraph(
                cast(tags.ParagraphVocabularyTag, paragraph_tag), item_path + "/*"
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

    def decode_table(self, element: tags.TableTag, path: str) -> models.Table:
        columns: list[models.TableColumn] | models.UnsetType = models.UNSET
        rows: list[models.TableRow] = []
        for child in cast(list[Node], element.children):
            if isinstance(child, tags.TableColgroupTag):
                columns = [
                    construct_model(
                        f"{path}/colgroup/col[{index}]",
                        lambda column=column: models.TableColumn(
                            width_type=cast(Any, column.width_type),
                            width=column.width,
                        ),
                    )
                    for index, column in enumerate(
                        cast(list[tags.TableColumnTag], child.children), 1
                    )
                ]
            else:
                body = cast(tags.TableBodyTag, child)
                rows = [
                    self.decode_table_row(row, f"{path}/tbody/tr[{index}]")
                    for index, row in enumerate(
                        cast(list[tags.TableRowTag], body.children), 1
                    )
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

    def decode_table_row(self, element: tags.TableRowTag, path: str) -> models.TableRow:
        return models.TableRow(
            cells=[
                self.decode_table_cell(cell, f"{path}/td[{index}]")
                for index, cell in enumerate(
                    cast(list[tags.TableCellTag], element.children), 1
                )
            ],
            min_height=element.min_height,
            prevent_overflow=element.prevent_overflow,
            is_header=element.is_header,
            row_key=(
                None if element.row_key is models.UNSET else cast(str, element.row_key)
            ),
        )

    def decode_table_cell(
        self, element: tags.TableCellTag, path: str
    ) -> models.TableCell:
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
        values = (
            {}
            if style_tag is None
            else self.decode_table_cell_style(style_tag, f"{path}/g:cell-style")
        )
        if (
            row_span != 1
            or column_span != 1
            or any(value is not models.UNSET for value in values.values())
        ):
            style = construct_model(
                path,
                lambda: models.TableCellStyle(
                    row_span=row_span, column_span=column_span, **cast(Any, values)
                ),
            )
        return models.TableCell(
            content=self.decode_structural_sequence(content_tags, path),
            style=style,
            cell_key=(
                None
                if element.cell_key is models.UNSET
                else cast(str, element.cell_key)
            ),
        )

    def decode_table_cell_style(
        self, element: tags.TableCellStyleTag, path: str
    ) -> dict[str, object]:
        values = {
            name: getattr(element, name)
            for name in tags.TableCellStyleTag.attribute_fields()
        }
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
            values[border_fields[type(border)]] = construct_model(
                f"{path}/{display_name(border.tag_name or '')}",
                lambda: models.TableCellBorder(
                    color=cast(models.Color | None, color),
                    width=cast(models.Dimension, border.width),
                    dash_style=cast(Any, border.dash_style),
                ),
            )
        return values

    def decode_paragraph(
        self, element: tags.ParagraphVocabularyTag, path: str
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
        for index, child in enumerate(cast(list[Node], element.children), 1):
            child_path = f"{path}/*[{index}]"
            if isinstance(child, tags.ParagraphStyleTag):
                if child.owned_named_style_type is not models.UNSET:
                    parse_error(
                        f"{path}/g:paragraph-style",
                        "named style type is owned by the paragraph element",
                    )
                style = self._decode_paragraph_style_tag(
                    child,
                    f"{path}/g:paragraph-style",
                    owning_named_style=named_style_type,
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
                    self.decode_paragraph_element(cast(Tag, child), child_path)
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

    def decode_paragraph_element(
        self, element: Tag, path: str
    ) -> models.ParagraphElement:
        link: models.Link | models.UnsetType = models.UNSET
        if isinstance(element, tags.ContentAnchorTag):
            link = self._decode_metadata_link(element)
            element = cast(Tag, cast(list[Node], element.children)[0])
            path = f"{path}/*[1]"
        if isinstance(element, tags.SpanTag):
            return self._decode_text_run_span(element, link, path)
        if isinstance(element, tags.EquationTag):
            return models.Equation()

        element = cast(tags.StyledParagraphElementTag, element)
        style_values = {
            name: getattr(element, name)
            for name in tags.StyledParagraphElementTag.attribute_fields()
        }
        text_style: models.TextStyle | models.UnsetType = models.UNSET
        if any(value is not models.UNSET for value in (*style_values.values(), link)):
            text_style = construct_model(
                path,
                lambda: models.TextStyle(**cast(Any, style_values), link=link),
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
        path: str,
        *,
        owning_named_style: object = models.UNSET,
    ) -> models.ParagraphStyle:
        values = {
            name: getattr(style_tag, name)
            for name in type(style_tag).attribute_fields()
            if name != "owned_named_style_type"
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
                border = cast(tags.ParagraphBorderTag, child)
                values[field_name] = self._decode_paragraph_border_tag(
                    border, f"{path}/{display_name(border.tag_name or '')}"
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

    def _decode_text_run_span(
        self, span_tag: tags.SpanTag, link: models.Link | models.UnsetType, path: str
    ) -> models.TextRun:
        style_values = {
            name: getattr(span_tag, name) for name in tags.SpanTag.attribute_fields()
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
            elif isinstance(child, tags.BreakTag):
                content += "\n"
            elif isinstance(child, tags.VerticalTabTag):
                content += "\v"
            else:
                content += "\f"
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
        return decoder.decode_document(_decode_tag(root, tags.HtmlTag, "/html"))
    except XHTMLParseError:
        raise
    except (ElementTree.ParseError, RecursionError) as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error
