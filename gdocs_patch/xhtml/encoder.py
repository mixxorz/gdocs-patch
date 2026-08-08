from typing import cast
from xml.etree import ElementTree

from gdocs_patch import models

from . import tags
from .base import (
    GDOCS_NAMESPACE,
    MAX_ELEMENT_DEPTH,
    MAX_XHTML_CHARACTERS,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    XHTMLParseError,
    _indent_xml,  # pyright: ignore[reportPrivateUsage]
    format_number,
    gdocs_name,
    require_boolean,
    require_dict,
    require_enum,
    require_integer,
    require_list,
    require_number,
    require_string,
    xhtml_name,
)
from .decoder import _Decoder  # pyright: ignore[reportPrivateUsage]
from .nodes import Encoder as XHTMLEncoder
from .nodes import Tag, Text

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
_CONTENT_ALIGNMENTS = {
    "CONTENT_ALIGNMENT_UNSPECIFIED",
    "CONTENT_ALIGNMENT_UNSUPPORTED",
    "TOP",
    "MIDDLE",
    "BOTTOM",
}
_WIDTH_TYPES = {"WIDTH_TYPE_UNSPECIFIED", "EVENLY_DISTRIBUTED", "FIXED_WIDTH"}
_DASH_STYLES = {"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"}
_AUTO_TEXT_TYPES = {"TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"}
_DATE_FORMATS = {
    "DATE_FORMAT_UNSPECIFIED",
    "DATE_FORMAT_CUSTOM",
    "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
    "DATE_FORMAT_MONTH_DAY_FULL",
    "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
    "DATE_FORMAT_ISO8601",
}
_TIME_FORMATS = {
    "TIME_FORMAT_UNSPECIFIED",
    "TIME_FORMAT_DISABLED",
    "TIME_FORMAT_HOUR_MINUTE",
    "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
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


def _omit_integer_default(
    value: object, default: int, field: str
) -> int | models.UnsetType:
    validated = require_integer(value, field)
    return models.UNSET if validated == default else validated


_PARAGRAPH_TAGS = {
    "NAMED_STYLE_TYPE_UNSPECIFIED": gdocs_name("named-style-unspecified"),
    "NORMAL_TEXT": xhtml_name("p"),
    "TITLE": gdocs_name("title"),
    "SUBTITLE": gdocs_name("subtitle"),
    **{f"HEADING_{level}": xhtml_name(f"h{level}") for level in range(1, 7)},
}


class _Encoder:
    def encode_document(self, document: models.Document) -> tags.HtmlTag:
        if not isinstance(document, models.Document):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("document must be a Document")
        require_list(document.tabs, "Document.tabs")
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
        if not isinstance(tab, models.Tab):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("Document.tabs entries must be Tab objects")
        children: list[Tag] = []
        if tab.content is not models.UNSET:
            if not isinstance(tab.content, models.DocumentTab):
                raise ValueError("Tab.content must be a DocumentTab or UNSET")
            children.append(self.encode_document_tab(tab.content))
        require_list(tab.children, "Tab.children")
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
            nesting_level=_omit_integer_default(
                tab.nesting_level, 0, "Tab.nesting_level"
            ),
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
            for name in tags.DocumentStyleTag.fields()
            if name != "children"
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
        require_list(styles, "DocumentTab.named_styles")
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
            name: getattr(style, name)
            for name in tags.SpanTag.fields()
            if name != "children"
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
            elif isinstance(link, models.HeadingLink):
                children.append(
                    tags.MetadataAnchorTag(
                        heading_id=link.heading_id, tab_id=link.tab_id
                    )
                )
            else:
                raise ValueError(f"unsupported link type {type(link).__name__}")
        return values, children

    def encode_body(self, body: models.Body) -> tags.DocumentBodyTag:
        require_list(body.content, "Body.content")
        if not body.content or not isinstance(body.content[0], models.SectionBreak):
            raise ValueError("Body.content must begin with SectionBreak")
        sections: list[tags.SectionTag] = []
        section_break: models.SectionBreak | None = None
        section_content: list[models.StructuralElement] = []
        for node in body.content:
            if isinstance(node, models.SectionBreak):
                if section_break is not None:
                    sections.append(self.encode_section(section_break, section_content))
                section_break = node
                section_content = []
            else:
                section_content.append(node)
        assert section_break is not None
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
                *self.encode_structural_sequence(content, body=True),
            ]
        )

    def encode_list_definitions(
        self, definitions: dict[str, models.ListDefinition]
    ) -> tags.ListDefinitionsTag:
        require_dict(definitions, "DocumentTab.lists")
        children: list[tags.ListDefinitionTag] = []
        for list_id, definition in definitions.items():
            require_list(definition.levels, "ListDefinition.levels")
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
            start_number=_omit_integer_default(
                level.start_number, 0, "ListLevel.start_number"
            ),
            children=children,
            **values,
        )

    def encode_section_style(
        self, section_break: models.SectionBreak
    ) -> tags.SectionStyleTag:
        style = section_break.style
        values = {
            name: getattr(style, name)
            for name in tags.SectionStyleTag.fields()
            if name != "children"
        }
        children: list[Tag] = []
        if style.columns is not models.UNSET:
            require_list(style.columns, "SectionStyle.columns")
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

    def encode_boolean_attribute(
        self, element: ElementTree.Element, name: str, value: bool | models.UnsetType
    ) -> None:
        if value is not models.UNSET:
            boolean = require_boolean(value, name)
            element.set(gdocs_name(name), "true" if boolean else "false")

    def encode_point_attribute(
        self,
        element: ElementTree.Element,
        name: str,
        value: models.Dimension | models.UnsetType,
    ) -> None:
        if value is not models.UNSET:
            if not isinstance(value, models.Dimension):
                raise ValueError(f"{name} must be a Dimension")
            element.set(
                gdocs_name(name),
                format_number(require_number(value.magnitude, f"{name}.magnitude")),
            )

    def encode_optional_color(
        self, parent: ElementTree.Element, name: str, color: models.Color | None
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        if color is None:
            element.set(gdocs_name("transparent"), "true")
        else:
            if not isinstance(color, models.Color):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError(f"{name} must be a Color or None")
            element.set(
                gdocs_name("red"),
                format_number(require_number(color.red, f"{name}.red")),
            )
            element.set(
                gdocs_name("green"),
                format_number(require_number(color.green, f"{name}.green")),
            )
            element.set(
                gdocs_name("blue"),
                format_number(require_number(color.blue, f"{name}.blue")),
            )

    def encode_segments(
        self,
        segments: dict[str, models.Segment],
        wrapper_name: str,
        wrapper_type: type[tags.HeadersTag]
        | type[tags.FootersTag]
        | type[tags.FootnotesTag],
    ) -> tags.HeadersTag | tags.FootersTag | tags.FootnotesTag:
        require_dict(segments, f"DocumentTab.{wrapper_name}")
        item_type: type[tags.SegmentTag] = {
            "headers": tags.HeaderTag,
            "footers": tags.FooterTag,
            "footnotes": tags.FootnoteTag,
        }[wrapper_name]
        children: list[tags.SegmentTag] = []
        for key, segment in segments.items():
            require_list(segment.content, "Segment.content")
            children.append(
                item_type(
                    key=require_string(key, f"DocumentTab.{wrapper_name} key"),
                    segment_id=require_string(segment.segment_id, "Segment.segment_id"),
                    children=self.encode_structural_sequence(segment.content),
                )
            )
        return wrapper_type(children=children)

    def encode_structural_sequence(
        self, elements: list[models.StructuralElement], body: bool = False
    ) -> list[Tag]:
        require_list(elements, "structural content")
        encoded: list[Tag] = []
        index = 0
        while index < len(elements):
            element = elements[index]
            if isinstance(element, models.SectionBreak):
                message = (
                    "SectionBreak must be projected as a section"
                    if body
                    else "SectionBreak is only valid in a body"
                )
                raise ValueError(message)
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
                    xml = self.encode_list(elements[index:end], key)  # type: ignore[arg-type]
                    index = end
                    encoded.append(self._structural_boundary_tag(xml))
                if key is not None:
                    continue
            elif isinstance(element, models.Table):
                encoded.append(
                    self._structural_boundary_tag(self.encode_table(element))
                )
            elif isinstance(element, models.TableOfContents):
                encoded.append(
                    tags.TableOfContentsTag(
                        children=self.encode_structural_sequence(element.content)
                    )
                )
            else:
                raise ValueError(
                    f"unsupported structural element {type(element).__name__}"
                )
            index += 1
        return encoded

    def _structural_boundary_tag(self, element: ElementTree.Element) -> Tag:
        tag_type = {
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
            )
        }[element.tag]
        return tag_type(payload=element)

    def bullet_group_key(self, paragraph: models.Paragraph) -> tuple[str, str] | None:
        bullet = paragraph.bullet
        if isinstance(bullet, models.Bullet):
            return ("existing", require_string(bullet.list_id, "Bullet.list_id"))
        if isinstance(bullet, models.BulletPreset):
            return (
                "preset",
                require_enum(bullet.preset, _BULLET_PRESETS, "BulletPreset.preset"),
            )
        if bullet is models.UNSET:
            return None
        raise ValueError(f"unsupported paragraph bullet object {type(bullet).__name__}")

    def encode_list(
        self, paragraphs: list[models.Paragraph], key: tuple[str, str]
    ) -> ElementTree.Element:
        require_list(paragraphs, "list paragraphs")
        element = ElementTree.Element(gdocs_name("list"))
        kind, identity = key
        element.set(
            gdocs_name("list-id" if kind == "existing" else "bullet-preset"), identity
        )
        for paragraph in paragraphs:
            item = ElementTree.SubElement(element, xhtml_name("li"))
            bullet = paragraph.bullet
            assert isinstance(bullet, (models.Bullet, models.BulletPreset))
            nesting_level = require_integer(
                bullet.nesting_level, f"{type(bullet).__name__}.nesting_level"
            )
            if nesting_level != 0:
                item.set(gdocs_name("nesting-level"), str(nesting_level))
            if (
                isinstance(bullet, models.Bullet)
                and bullet.text_style is not models.UNSET
            ):
                values, metadata_children = self._encode_metadata_text_style_tag(
                    bullet.text_style
                )
                metadata = tags.BulletStyleTag(children=metadata_children, **values)
                if metadata_children or any(
                    value is not models.UNSET for value in values.values()
                ):
                    item.append(XHTMLEncoder().encode_element(metadata))
            item.append(XHTMLEncoder().encode_element(self.encode_paragraph(paragraph)))
        return element

    def encode_table(self, table: models.Table) -> ElementTree.Element:
        require_list(table.rows, "Table.rows")
        element = ElementTree.Element(xhtml_name("table"))
        if table.table_key is not None:
            element.set(
                gdocs_name("table-key"),
                require_string(table.table_key, "Table.table_key"),
            )
        if table.column_styles is not models.UNSET:
            require_list(table.column_styles, "Table.column_styles")
            colgroup = ElementTree.SubElement(element, xhtml_name("colgroup"))
            for column in cast(list[models.TableColumn], table.column_styles):
                child = ElementTree.SubElement(colgroup, xhtml_name("col"))
                child.set(
                    gdocs_name("width-type"),
                    require_enum(
                        column.width_type, _WIDTH_TYPES, "TableColumn.width_type"
                    ),
                )
                self.encode_point_attribute(child, "width", column.width)
        tbody = ElementTree.SubElement(element, xhtml_name("tbody"))
        for row in table.rows:
            tbody.append(self.encode_table_row(row))
        return element

    def encode_table_row(self, row: models.TableRow) -> ElementTree.Element:
        require_list(row.cells, "TableRow.cells")
        element = ElementTree.Element(xhtml_name("tr"))
        if row.row_key is not None:
            element.set(
                gdocs_name("row-key"), require_string(row.row_key, "TableRow.row_key")
            )
        self.encode_point_attribute(element, "min-height", row.min_height)
        self.encode_boolean_attribute(element, "prevent-overflow", row.prevent_overflow)
        self.encode_boolean_attribute(element, "is-header", row.is_header)
        for cell in row.cells:
            element.append(self.encode_table_cell(cell))
        return element

    def encode_table_cell(self, cell: models.TableCell) -> ElementTree.Element:
        require_list(cell.content, "TableCell.content")
        element = ElementTree.Element(xhtml_name("td"))
        if cell.cell_key is not None:
            element.set(
                gdocs_name("cell-key"),
                require_string(cell.cell_key, "TableCell.cell_key"),
            )
        if cell.style is not models.UNSET:
            style = cast(models.TableCellStyle, cell.style)
            row_span = require_integer(style.row_span, "TableCellStyle.row_span")
            column_span = require_integer(
                style.column_span, "TableCellStyle.column_span"
            )
            if row_span != 1:
                element.set("rowspan", str(row_span))
            if column_span != 1:
                element.set("colspan", str(column_span))
            metadata = self.encode_table_cell_style(style)
            if metadata is not None:
                element.append(metadata)
        element.extend(
            XHTMLEncoder().encode_element(tag)
            for tag in self.encode_structural_sequence(cell.content, body=False)
        )
        return element

    def encode_table_cell_style(
        self, style: models.TableCellStyle
    ) -> ElementTree.Element | None:
        element = ElementTree.Element(gdocs_name("cell-style"))
        if style.content_alignment is not models.UNSET:
            element.set(
                gdocs_name("content-alignment"),
                require_enum(
                    style.content_alignment,
                    _CONTENT_ALIGNMENTS,
                    "TableCellStyle.content_alignment",
                ),
            )
        for value, name in (
            (style.padding_left, "padding-left"),
            (style.padding_right, "padding-right"),
            (style.padding_top, "padding-top"),
            (style.padding_bottom, "padding-bottom"),
        ):
            self.encode_point_attribute(element, name, value)
        if style.background_color is not models.UNSET:
            self.encode_optional_color(
                element,
                "background-color",
                cast(models.Color | None, style.background_color),
            )
        for value, name in (
            (style.border_left, "border-left"),
            (style.border_right, "border-right"),
            (style.border_top, "border-top"),
            (style.border_bottom, "border-bottom"),
        ):
            if value is not models.UNSET:
                self.encode_table_cell_border(
                    element, name, cast(models.TableCellBorder, value)
                )
        return element if element.attrib or list(element) else None

    def encode_table_cell_border(
        self, parent: ElementTree.Element, name: str, border: models.TableCellBorder
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        element.set(
            gdocs_name("dash-style"),
            require_enum(border.dash_style, _DASH_STYLES, "TableCellBorder.dash_style"),
        )
        self.encode_point_attribute(element, "width", border.width)
        self.encode_optional_color(element, "color", border.color)

    def encode_paragraph(
        self, paragraph: models.Paragraph
    ) -> tags.ParagraphVocabularyTag:
        tag_type: type[tags.ParagraphVocabularyTag] = tags.GenericParagraphTag
        style: models.ParagraphStyle | None = None
        if paragraph.style is not models.UNSET:
            style = cast(models.ParagraphStyle, paragraph.style)
            if style.named_style_type is not models.UNSET:
                named_style_type = require_enum(
                    style.named_style_type,
                    _NAMED_STYLE_TYPES,
                    "ParagraphStyle.named_style_type",
                )
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
                }[named_style_type]

        require_list(paragraph.elements, "Paragraph.elements")
        children: list[Tag] = []
        metadata = None if style is None else self._encode_paragraph_style_tag(style)
        if metadata is not None:
            children.append(metadata)
        if paragraph.positioned_object_ids is not models.UNSET:
            require_list(
                paragraph.positioned_object_ids, "Paragraph.positioned_object_ids"
            )
            children.append(
                tags.PositionedObjectsTag(
                    children=[
                        tags.PositionedObjectTag(
                            object_id=require_string(
                                object_id, "Paragraph.positioned_object_ids entry"
                            )
                        )
                        for object_id in cast(
                            list[str], paragraph.positioned_object_ids
                        )
                    ]
                )
            )
        children.extend(
            self.encode_paragraph_element(item) for item in paragraph.elements
        )
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
        if isinstance(link, models.HeadingLink):
            return tags.ContentAnchorTag(
                heading_id=link.heading_id, tab_id=link.tab_id, children=[child]
            )
        raise ValueError(f"unsupported link type {type(link).__name__}")

    def encode_paragraph_element(self, item: models.ParagraphElement) -> Tag:
        if isinstance(item, models.TextRun):
            span, link = self._encode_text_run_span(item)
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
        elif isinstance(item, models.RichLink):
            tag_type = tags.RichLinkTag
            values.update(
                rich_link_id=item.rich_link_id,
                uri=item.uri,
                title=item.title,
                mime_type=item.mime_type,
            )
        else:
            raise ValueError(f"unsupported paragraph element {type(item).__name__}")

        link: models.Link | models.UnsetType = models.UNSET
        if item.text_style is not models.UNSET:
            style = cast(models.TextStyle, item.text_style)
            link = style.link
            values.update(
                (name, getattr(style, name))
                for name in tags.StyledParagraphElementTag.fields()
                if name != "children"
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
            for name in paragraph_style_tag_type.fields()
            if name not in {"children", "owned_named_style_type"}
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
            require_list(style.tab_stops, "ParagraphStyle.tab_stops")
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
        self, run: models.TextRun
    ) -> tuple[tags.SpanTag, models.Link | models.UnsetType]:
        children: list[Text | tags.BreakTag] = []
        parts = run.content.split("\n")
        if parts[0]:
            children.append(Text(parts[0]))
        for part in parts[1:]:
            children.append(tags.BreakTag())
            if part:
                children.append(Text(part))

        link: models.Link | models.UnsetType = models.UNSET
        style_values: dict[str, object] = {}
        if run.text_style is not models.UNSET:
            style = cast(models.TextStyle, run.text_style)
            link = style.link
            style_values = {
                name: getattr(style, name)
                for name in tags.SpanTag.fields()
                if name != "children"
            }

        return tags.SpanTag(children=children, **style_values), link


def _is_xml_10_character(character: str) -> bool:
    codepoint = ord(character)
    return (
        codepoint in (0x9, 0xA, 0xD)
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def _validate_generated_tree(root: ElementTree.Element) -> None:
    pending = [(root, 1)]
    while pending:
        element, depth = pending.pop()
        if depth > MAX_ELEMENT_DEPTH:
            raise ValueError(f"XML element depth exceeds {MAX_ELEMENT_DEPTH}")
        values = [element.text, element.tail, *element.attrib.values()]
        for value in values:
            if value is not None and not isinstance(value, str):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise ValueError("XML text and attribute values must be strings")
            if value is not None and any(
                not _is_xml_10_character(character) for character in value
            ):
                raise ValueError("document contains a character forbidden by XML 1.0")
        pending.extend((child, depth + 1) for child in element)


def _validate_encoded_tree(root: ElementTree.Element) -> None:
    try:
        decoder = _Decoder()
        decoder.decode_document(decoder.decode_tag(root, tags.HtmlTag, "/html"))
    except XHTMLParseError as error:
        raise ValueError(
            f"document model cannot be encoded as valid XHTML: {error}"
        ) from error


def serialize_document(document: models.Document) -> str:
    ElementTree.register_namespace("", XHTML_NAMESPACE)
    ElementTree.register_namespace("g", GDOCS_NAMESPACE)
    try:
        root = XHTMLEncoder().encode_element(_Encoder().encode_document(document))
    except (AttributeError, KeyError, RecursionError, TypeError) as error:
        raise ValueError(f"invalid mutated document model: {error}") from error
    _validate_generated_tree(root)
    _validate_encoded_tree(root)
    _indent_xml(root)
    xml = ElementTree.tostring(
        root, encoding="unicode", short_empty_elements=True
    ).replace("\r", "&#13;")
    output = f"{XML_DECLARATION}\n{xml}\n"
    if len(output) > MAX_XHTML_CHARACTERS:
        raise ValueError(f"XHTML output exceeds {MAX_XHTML_CHARACTERS} characters")
    return output
