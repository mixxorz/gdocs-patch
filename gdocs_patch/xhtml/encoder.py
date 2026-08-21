from typing import TypeVar, cast
from xml.etree import ElementTree

from gdocs_patch import models

from . import tags
from .base import (
    GDOCS_NAMESPACE,
    XHTML_NAMESPACE,
    XML_DECLARATION,
)
from .nodes import Tag, TagEncoder, Text

T = TypeVar("T")


def _omit_default(value: T, default: T) -> T | models.UnsetType:
    return models.UNSET if value == default else value


class _DocumentEncoder:
    def encode_document(self, document: models.Document) -> tags.HtmlTag:
        return tags.HtmlTag(
            document_id=document.document_id,
            title=document.title,
            revision_id=document.revision_id,
            suggestions_view_mode=document.suggestions_view_mode,
            children=[
                tags.BodyTag(children=[self.encode_tab(tab) for tab in document.tabs])
            ],
        )

    def encode_tab(self, tab: models.Tab) -> tags.TabTag:
        children: list[Tag] = []
        if tab.content is not models.UNSET:
            children.append(
                self.encode_document_tab(cast(models.DocumentTab, tab.content))
            )
        if tab.children:
            children.append(
                tags.ChildTabsTag(
                    children=[self.encode_tab(child) for child in tab.children]
                )
            )
        return tags.TabTag(
            tab_id=tab.tab_id,
            title=tab.title,
            index=tab.index,
            nesting_level=_omit_default(tab.nesting_level, 0),
            parent_tab_id=tab.parent_tab_id,
            icon_emoji=tab.icon_emoji,
            children=children,
        )

    def encode_document_tab(
        self, document_tab: models.DocumentTab
    ) -> tags.DocumentTabTag:
        children: list[Tag] = []
        if document_tab.document_style is not models.UNSET:
            children.append(
                self.encode_document_style(
                    cast(models.DocumentStyle, document_tab.document_style)
                )
            )
        if document_tab.named_styles is not models.UNSET:
            children.append(
                self.encode_named_styles(
                    cast(list[models.NamedStyle], document_tab.named_styles)
                )
            )
        if document_tab.lists is not models.UNSET:
            children.append(
                self.encode_list_definitions(
                    cast(dict[str, models.ListDefinition], document_tab.lists)
                )
            )
        if document_tab.body is not models.UNSET:
            children.append(self.encode_body(cast(models.Body, document_tab.body)))
        for value, wrapper_name, wrapper_type in (
            (document_tab.headers, "headers", tags.HeadersTag),
            (document_tab.footers, "footers", tags.FootersTag),
            (document_tab.footnotes, "footnotes", tags.FootnotesTag),
        ):
            if value is models.UNSET:
                continue
            children.append(
                self.encode_segments(
                    cast(dict[str, models.Segment], value), wrapper_name, wrapper_type
                )
            )
        return tags.DocumentTabTag(children=children)

    def encode_document_style(
        self, style: models.DocumentStyle
    ) -> tags.DocumentStyleTag:
        values = {
            name: getattr(style, name)
            for name in tags.DocumentStyleTag.attribute_fields()
        }
        children: list[Tag] = []
        if style.background_color is not models.UNSET:
            children.append(
                tags.BackgroundColorTag(
                    color=cast(models.Color | None, style.background_color)
                )
            )
        return tags.DocumentStyleTag(children=children, **values)

    def encode_named_styles(
        self, styles: list[models.NamedStyle]
    ) -> tags.NamedStylesTag:
        children: list[tags.NamedStyleTag] = []
        for style in styles:
            values, metadata = self._encode_metadata_text_style_tag(style.text_style)
            if style.paragraph_style is not models.UNSET:
                paragraph = self._encode_paragraph_style_tag(
                    cast(models.ParagraphStyle, style.paragraph_style), named_style=True
                )
                if paragraph is not None:
                    metadata.append(paragraph)
            children.append(
                tags.NamedStyleTag(
                    named_style_type=style.named_style_type,
                    children=metadata,
                    **values,
                )
            )
        return tags.NamedStylesTag(children=children)

    def _encode_metadata_text_style_tag(
        self, style: models.TextStyle | models.UnsetType
    ) -> tuple[dict[str, object], list[Tag]]:
        if style is models.UNSET:
            return {}, []
        style = cast(models.TextStyle, style)
        values = {
            name: getattr(style, name) for name in tags.SpanTag.attribute_fields()
        }
        children: list[Tag] = []
        if style.link is not models.UNSET:
            link = cast(models.Link, style.link)
            if isinstance(link, models.UrlLink):
                children.append(tags.MetadataAnchorTag(href=link.url))
            elif isinstance(link, models.TabLink):
                children.append(tags.MetadataAnchorTag(tab_id=link.tab_id))
            elif isinstance(link, models.BookmarkLink):
                children.append(
                    tags.MetadataAnchorTag(
                        bookmark_id=link.bookmark_id, tab_id=link.tab_id
                    )
                )
            else:
                heading_link = cast(models.HeadingLink, link)
                children.append(
                    tags.MetadataAnchorTag(
                        heading_id=heading_link.heading_id,
                        tab_id=heading_link.tab_id,
                    )
                )
        return values, children

    def encode_body(self, body: models.Body) -> tags.DocumentBodyTag:
        sections: list[tags.SectionTag] = []
        section_break = cast(models.SectionBreak, body.content[0])
        section_content: list[models.StructuralElement] = []
        for node in body.content[1:]:
            if isinstance(node, models.SectionBreak):
                sections.append(self.encode_section(section_break, section_content))
                section_break = node
                section_content = []
            else:
                section_content.append(node)
        sections.append(self.encode_section(section_break, section_content))
        return tags.DocumentBodyTag(children=sections)

    def encode_section(
        self,
        section_break: models.SectionBreak,
        content: list[models.StructuralElement],
    ) -> tags.SectionTag:
        return tags.SectionTag(
            children=[
                self.encode_section_style(section_break),
                *self.encode_structural_sequence(content),
            ]
        )

    def encode_list_definitions(
        self, definitions: dict[str, models.ListDefinition]
    ) -> tags.ListDefinitionsTag:
        children: list[tags.ListDefinitionTag] = []
        for list_id, definition in definitions.items():
            children.append(
                tags.ListDefinitionTag(
                    list_id=list_id,
                    children=[
                        self.encode_list_level(level) for level in definition.levels
                    ],
                )
            )
        return tags.ListDefinitionsTag(children=children)

    def encode_list_level(self, level: models.ListLevel) -> tags.ListLevelTag:
        values, children = self._encode_metadata_text_style_tag(level.text_style)
        return tags.ListLevelTag(
            glyph_format=level.glyph_format,
            glyph_type=level.glyph_type,
            glyph_symbol=level.glyph_symbol,
            alignment=(
                models.UNSET
                if level.alignment == "BULLET_ALIGNMENT_UNSPECIFIED"
                else level.alignment
            ),
            indent_first_line=level.indent_first_line,
            indent_start=level.indent_start,
            start_number=_omit_default(level.start_number, 0),
            children=children,
            **values,
        )

    def encode_section_style(
        self, section_break: models.SectionBreak
    ) -> tags.SectionStyleTag:
        style = section_break.style
        values = {
            name: getattr(style, name)
            for name in tags.SectionStyleTag.attribute_fields()
        }
        children: list[Tag] = []
        if style.columns is not models.UNSET:
            children.append(
                tags.SectionColumnsTag(
                    children=[
                        tags.SectionColumnTag(
                            width=column.width,
                            padding_end=column.padding_end,
                        )
                        for column in cast(list[models.SectionColumn], style.columns)
                    ]
                )
            )
        return tags.SectionStyleTag(children=children, **values)

    def encode_segments(
        self,
        segments: dict[str, models.Segment],
        wrapper_name: str,
        wrapper_type: type[tags.HeadersTag]
        | type[tags.FootersTag]
        | type[tags.FootnotesTag],
    ) -> tags.HeadersTag | tags.FootersTag | tags.FootnotesTag:
        item_type: type[tags.SegmentTag] = {
            "headers": tags.HeaderTag,
            "footers": tags.FooterTag,
            "footnotes": tags.FootnoteTag,
        }[wrapper_name]
        children: list[tags.SegmentTag] = []
        for key, segment in segments.items():
            children.append(
                item_type(
                    key=key,
                    segment_id=segment.segment_id,
                    children=self.encode_structural_sequence(segment.content),
                )
            )
        return wrapper_type(children=children)

    def encode_structural_sequence(
        self, elements: list[models.StructuralElement]
    ) -> list[Tag]:
        encoded: list[Tag] = []
        index = 0
        while index < len(elements):
            element = elements[index]
            if isinstance(element, models.Paragraph):
                key = self.bullet_group_key(element)
                if key is None:
                    encoded.append(self.encode_paragraph(element))
                else:
                    end = index + 1
                    while end < len(elements):
                        candidate = elements[end]
                        if not isinstance(candidate, models.Paragraph):
                            break
                        if self.bullet_group_key(candidate) != key:
                            break
                        end += 1
                    encoded.append(
                        self.encode_list(elements[index:end], key)  # type: ignore[arg-type]
                    )
                    index = end
                if key is not None:
                    continue
            elif isinstance(element, models.Table):
                encoded.append(self.encode_table(element))
            else:
                table_of_contents = cast(models.TableOfContents, element)
                encoded.append(
                    tags.TableOfContentsTag(
                        children=self.encode_structural_sequence(
                            table_of_contents.content
                        )
                    )
                )
            index += 1
        return encoded

    def bullet_group_key(self, paragraph: models.Paragraph) -> tuple[str, str] | None:
        bullet = paragraph.bullet
        if isinstance(bullet, models.Bullet):
            return ("existing", bullet.list_id)
        if isinstance(bullet, models.BulletPreset):
            return ("preset", bullet.preset)
        return None

    def encode_list(
        self, paragraphs: list[models.Paragraph], key: tuple[str, str]
    ) -> tags.ListTag:
        kind, identity = key
        items: list[tags.ListItemTag] = []
        for paragraph in paragraphs:
            bullet = cast(models.Bullet | models.BulletPreset, paragraph.bullet)
            children: list[Tag] = []
            if (
                isinstance(bullet, models.Bullet)
                and bullet.text_style is not models.UNSET
            ):
                values, metadata_children = self._encode_metadata_text_style_tag(
                    bullet.text_style
                )
                if metadata_children or any(
                    value is not models.UNSET for value in values.values()
                ):
                    children.append(
                        tags.BulletStyleTag(children=metadata_children, **values)
                    )
            children.append(self.encode_paragraph(paragraph))
            items.append(
                tags.ListItemTag(
                    nesting_level=_omit_default(bullet.nesting_level, 0),
                    children=children,
                )
            )
        return tags.ListTag(
            list_id=identity if kind == "existing" else models.UNSET,
            bullet_preset=identity if kind == "preset" else models.UNSET,
            children=items,
        )

    def encode_table(self, table: models.Table) -> tags.TableTag:
        children: list[Tag] = []
        if table.column_styles is not models.UNSET:
            children.append(
                tags.TableColgroupTag(
                    children=[
                        tags.TableColumnTag(
                            width_type=column.width_type, width=column.width
                        )
                        for column in cast(
                            list[models.TableColumn], table.column_styles
                        )
                    ]
                )
            )
        children.append(
            tags.TableBodyTag(
                children=[self.encode_table_row(row) for row in table.rows]
            )
        )
        return tags.TableTag(
            table_key=models.UNSET if table.table_key is None else table.table_key,
            children=children,
        )

    def encode_table_row(self, row: models.TableRow) -> tags.TableRowTag:
        return tags.TableRowTag(
            row_key=models.UNSET if row.row_key is None else row.row_key,
            min_height=row.min_height,
            prevent_overflow=row.prevent_overflow,
            is_header=row.is_header,
            children=[self.encode_table_cell(cell) for cell in row.cells],
        )

    def encode_table_cell(self, cell: models.TableCell) -> tags.TableCellTag:
        row_span: int | models.UnsetType = models.UNSET
        column_span: int | models.UnsetType = models.UNSET
        children: list[Tag] = []
        if cell.style is not models.UNSET:
            style = cast(models.TableCellStyle, cell.style)
            row_span = _omit_default(style.row_span, 1)
            column_span = _omit_default(style.column_span, 1)
            metadata = self.encode_table_cell_style(style)
            if metadata is not None:
                children.append(metadata)
        children.extend(self.encode_structural_sequence(cell.content))
        return tags.TableCellTag(
            cell_key=models.UNSET if cell.cell_key is None else cell.cell_key,
            row_span=row_span,
            column_span=column_span,
            children=children,
        )

    def encode_table_cell_style(
        self, style: models.TableCellStyle
    ) -> tags.TableCellStyleTag | None:
        values = {
            name: getattr(style, name)
            for name in tags.TableCellStyleTag.attribute_fields()
        }
        children: list[Tag] = []
        if style.background_color is not models.UNSET:
            children.append(
                tags.TableCellBackgroundColorTag(
                    color=cast(models.Color | None, style.background_color)
                )
            )
        border_tags: tuple[tuple[str, type[tags.TableCellBorderTag]], ...] = (
            ("border_left", tags.TableCellBorderLeftTag),
            ("border_right", tags.TableCellBorderRightTag),
            ("border_top", tags.TableCellBorderTopTag),
            ("border_bottom", tags.TableCellBorderBottomTag),
        )
        for name, tag_type in border_tags:
            value = getattr(style, name)
            if value is models.UNSET:
                continue
            border = cast(models.TableCellBorder, value)
            children.append(
                tag_type(
                    dash_style=border.dash_style,
                    width=border.width,
                    children=[tags.ColorTag(color=border.color)],
                )
            )
        if not children and all(value is models.UNSET for value in values.values()):
            return None
        return tags.TableCellStyleTag(children=children, **values)

    def encode_paragraph(
        self, paragraph: models.Paragraph
    ) -> tags.ParagraphVocabularyTag:
        tag_type: type[tags.ParagraphVocabularyTag] = tags.GenericParagraphTag
        style: models.ParagraphStyle | None = None
        if paragraph.style is not models.UNSET:
            style = cast(models.ParagraphStyle, paragraph.style)
            if style.named_style_type is not models.UNSET:
                tag_type = {
                    "NAMED_STYLE_TYPE_UNSPECIFIED": tags.UnspecifiedParagraphTag,
                    "NORMAL_TEXT": tags.ParagraphTag,
                    "TITLE": tags.TitleTag,
                    "SUBTITLE": tags.SubtitleTag,
                    "HEADING_1": tags.Heading1Tag,
                    "HEADING_2": tags.Heading2Tag,
                    "HEADING_3": tags.Heading3Tag,
                    "HEADING_4": tags.Heading4Tag,
                    "HEADING_5": tags.Heading5Tag,
                    "HEADING_6": tags.Heading6Tag,
                }[cast(str, style.named_style_type)]

        children: list[Tag] = []
        metadata = None if style is None else self._encode_paragraph_style_tag(style)
        if metadata is not None:
            children.append(metadata)
        if paragraph.positioned_object_ids is not models.UNSET:
            children.append(
                tags.PositionedObjectsTag(
                    children=[
                        tags.PositionedObjectTag(object_id=object_id)
                        for object_id in cast(
                            list[str], paragraph.positioned_object_ids
                        )
                    ]
                )
            )
        has_terminal_newline = bool(
            paragraph.elements
            and isinstance(paragraph.elements[-1], models.TextRun)
            and paragraph.elements[-1].content.endswith("\n")
        )
        for index, item in enumerate(paragraph.elements):
            children.append(
                self.encode_paragraph_element(
                    item,
                    omit_terminal_newline=(
                        has_terminal_newline and index == len(paragraph.elements) - 1
                    ),
                )
            )
        if not has_terminal_newline:
            children.append(tags.SpanTag())
        return tag_type(children=children)

    def _encode_content_link(
        self, child: Tag, link: models.Link | models.UnsetType
    ) -> Tag:
        if link is models.UNSET:
            return child
        link = cast(models.Link, link)
        if isinstance(link, models.UrlLink):
            return tags.ContentAnchorTag(href=link.url, children=[child])
        if isinstance(link, models.TabLink):
            return tags.ContentAnchorTag(tab_id=link.tab_id, children=[child])
        if isinstance(link, models.BookmarkLink):
            return tags.ContentAnchorTag(
                bookmark_id=link.bookmark_id, tab_id=link.tab_id, children=[child]
            )
        heading_link = cast(models.HeadingLink, link)
        return tags.ContentAnchorTag(
            heading_id=heading_link.heading_id,
            tab_id=heading_link.tab_id,
            children=[child],
        )

    def encode_paragraph_element(
        self,
        item: models.ParagraphElement,
        *,
        omit_terminal_newline: bool = False,
    ) -> Tag:
        if isinstance(item, models.TextRun):
            span, link = self._encode_text_run_span(
                item, omit_terminal_newline=omit_terminal_newline
            )
            return self._encode_content_link(span, link)
        if isinstance(item, models.Equation):
            return tags.EquationTag()

        tag_type: type[tags.StyledParagraphElementTag]
        values: dict[str, object] = {}
        if isinstance(item, models.AutoText):
            tag_type = tags.AutoTextTag
            values["auto_text_type"] = item.auto_text_type
        elif isinstance(item, models.ColumnBreak):
            tag_type = tags.ColumnBreakTag
        elif isinstance(item, models.DateElement):
            tag_type = tags.DateElementTag
            values.update(
                date_id=item.date_id,
                date_format=item.date_format,
                display_text=item.display_text,
                locale=item.locale,
                time_format=item.time_format,
                time_zone_id=item.time_zone_id,
                timestamp=item.timestamp,
            )
        elif isinstance(item, models.FootnoteReference):
            tag_type = tags.FootnoteReferenceTag
            values.update(
                footnote_id=item.footnote_id, footnote_number=item.footnote_number
            )
        elif isinstance(item, models.HorizontalRule):
            tag_type = tags.HorizontalRuleTag
        elif isinstance(item, models.InlineObjectReference):
            tag_type = tags.InlineObjectReferenceTag
            values["inline_object_id"] = item.inline_object_id
        elif isinstance(item, models.PageBreak):
            tag_type = tags.PageBreakTag
        elif isinstance(item, models.PersonReference):
            tag_type = tags.PersonReferenceTag
            values.update(person_id=item.person_id, email=item.email, name=item.name)
        else:
            rich_link = cast(models.RichLink, item)
            tag_type = tags.RichLinkTag
            values.update(
                rich_link_id=rich_link.rich_link_id,
                uri=rich_link.uri,
                title=rich_link.title,
                mime_type=rich_link.mime_type,
            )

        link: models.Link | models.UnsetType = models.UNSET
        text_style = cast(
            models.TextStyle | models.UnsetType, getattr(item, "text_style")
        )
        if text_style is not models.UNSET:
            style = cast(models.TextStyle, text_style)
            link = style.link
            values.update(
                (name, getattr(style, name))
                for name in tags.StyledParagraphElementTag.attribute_fields()
            )
        return self._encode_content_link(tag_type(**values), link)

    def _encode_paragraph_style_tag(
        self,
        style: models.ParagraphStyle,
        *,
        named_style: bool = False,
    ) -> tags.ParagraphStyleTag | None:
        paragraph_style_tag_type = (
            tags.NamedParagraphStyleTag if named_style else tags.ParagraphStyleTag
        )
        values = {
            name: getattr(style, name)
            for name in paragraph_style_tag_type.attribute_fields()
            if name != "owned_named_style_type"
        }
        children: list[Tag] = []
        border_tags: tuple[tuple[str, type[tags.ParagraphBorderTag]], ...] = (
            ("border_between", tags.BorderBetweenTag),
            ("border_top", tags.BorderTopTag),
            ("border_bottom", tags.BorderBottomTag),
            ("border_left", tags.BorderLeftTag),
            ("border_right", tags.BorderRightTag),
        )
        for name, border_tag_type in border_tags:
            value = getattr(style, name)
            if value is models.UNSET:
                continue
            border = cast(models.ParagraphBorder, value)
            children.append(
                border_tag_type(
                    dash_style=border.dash_style,
                    width=border.width,
                    padding=border.padding,
                    children=[tags.ColorTag(color=border.color)],
                )
            )
        if style.shading_color is not models.UNSET:
            children.append(
                tags.ShadingColorTag(
                    color=cast(models.Color | None, style.shading_color)
                )
            )
        if style.tab_stops is not models.UNSET:
            children.append(
                tags.TabStopsTag(
                    children=[
                        tags.TabStopTag(alignment=stop.alignment, offset=stop.offset)
                        for stop in cast(list[models.TabStop], style.tab_stops)
                    ]
                )
            )

        if not children and all(value is models.UNSET for value in values.values()):
            return None
        return paragraph_style_tag_type(children=children, **values)

    def _encode_text_run_span(
        self,
        run: models.TextRun,
        *,
        omit_terminal_newline: bool = False,
    ) -> tuple[tags.SpanTag, models.Link | models.UnsetType]:
        children: list[
            Text | tags.BreakTag | tags.VerticalTabTag | tags.FormFeedTag
        ] = []
        text: list[str] = []
        control_tags = {
            "\n": tags.BreakTag,
            "\v": tags.VerticalTabTag,
            "\f": tags.FormFeedTag,
        }
        content = run.content[:-1] if omit_terminal_newline else run.content
        for character in content:
            tag_type = control_tags.get(character)
            if tag_type is None:
                text.append(character)
                continue
            if text:
                children.append(Text("".join(text)))
                text = []
            children.append(tag_type())
        if text:
            children.append(Text("".join(text)))

        link: models.Link | models.UnsetType = models.UNSET
        style_values: dict[str, object] = {}
        if run.text_style is not models.UNSET:
            style = cast(models.TextStyle, run.text_style)
            link = style.link
            style_values = {
                name: getattr(style, name) for name in tags.SpanTag.attribute_fields()
            }

        return tags.SpanTag(children=children, **style_values), link


def _indent_xml(element: ElementTree.Element, level: int = 0) -> None:
    if element.tag == tags.SpanTag.tag_name:
        return
    children = list(element)
    if not children:
        return

    indentation = "\n" + "  " * (level + 1)
    if element.text is None or not element.text.strip():
        element.text = indentation
    for child in children:
        _indent_xml(child, level + 1)
        if child.tail is None or not child.tail.strip():
            child.tail = indentation
    children[-1].tail = "\n" + "  " * level


def serialize_document(document: models.Document) -> str:
    ElementTree.register_namespace("", XHTML_NAMESPACE)
    ElementTree.register_namespace("g", GDOCS_NAMESPACE)
    root = TagEncoder().encode_element(_DocumentEncoder().encode_document(document))
    _indent_xml(root)
    xml = ElementTree.tostring(
        root, encoding="unicode", short_empty_elements=True
    ).replace("\r", "&#13;")
    return f"{XML_DECLARATION}\n{xml}\n"
