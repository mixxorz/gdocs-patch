from typing import cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    AutoText,
    Body,
    Bullet,
    BulletPreset,
    Color,
    ColumnBreak,
    DateElement,
    Dimension,
    Document,
    DocumentStyle,
    DocumentTab,
    Equation,
    FootnoteReference,
    HorizontalRule,
    InlineObjectReference,
    ListDefinition,
    ListLevel,
    NamedStyle,
    PageBreak,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
    PersonReference,
    RichLink,
    SectionBreak,
    SectionColumn,
    Segment,
    StructuralElement,
    Tab,
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableOfContents,
    TableRow,
    TabStop,
    TextRun,
    TextStyle,
    UnsetType,
)

from .base import (
    GDOCS_NAMESPACE,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    _indent_xml,  # pyright: ignore[reportPrivateUsage]
    encode_text_style,
    format_number,
    gdocs_name,
    xhtml_name,
)

_PARAGRAPH_TAGS = {
    "NAMED_STYLE_TYPE_UNSPECIFIED": gdocs_name("named-style-unspecified"),
    "NORMAL_TEXT": xhtml_name("p"),
    "TITLE": gdocs_name("title"),
    "SUBTITLE": gdocs_name("subtitle"),
    **{f"HEADING_{level}": xhtml_name(f"h{level}") for level in range(1, 7)},
}


class _Encoder:
    def encode_document(self, document: Document) -> ElementTree.Element:
        root = ElementTree.Element(xhtml_name("html"))
        root.set(gdocs_name("document-id"), document.document_id)
        root.set(gdocs_name("title"), document.title)
        if document.revision_id is not UNSET:
            root.set(gdocs_name("revision-id"), cast(str, document.revision_id))
        if document.suggestions_view_mode is not UNSET:
            root.set(
                gdocs_name("suggestions-view-mode"),
                cast(str, document.suggestions_view_mode),
            )

        body = ElementTree.SubElement(root, xhtml_name("body"))
        for tab in document.tabs:
            body.append(self.encode_tab(tab))
        return root

    def encode_tab(self, tab: Tab) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("tab"))
        element.set(gdocs_name("tab-id"), tab.tab_id)
        element.set(gdocs_name("title"), tab.title)
        element.set(gdocs_name("index"), str(tab.index))
        if tab.nesting_level != 0:
            element.set(gdocs_name("nesting-level"), str(tab.nesting_level))
        if tab.parent_tab_id is not UNSET:
            element.set(gdocs_name("parent-tab-id"), cast(str, tab.parent_tab_id))
        if tab.icon_emoji is not UNSET:
            element.set(gdocs_name("icon-emoji"), cast(str, tab.icon_emoji))

        if tab.content is not UNSET:
            element.append(self.encode_document_tab(cast(DocumentTab, tab.content)))
        if tab.children:
            child_tabs = ElementTree.SubElement(element, gdocs_name("child-tabs"))
            for child in tab.children:
                child_tabs.append(self.encode_tab(child))
        return element

    def encode_document_tab(self, document_tab: DocumentTab) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("document-tab"))
        if document_tab.document_style is not UNSET:
            element.append(
                self.encode_document_style(
                    cast(DocumentStyle, document_tab.document_style)
                )
            )
        if document_tab.named_styles is not UNSET:
            element.append(
                self.encode_named_styles(
                    cast(list[NamedStyle], document_tab.named_styles)
                )
            )
        if document_tab.lists is not UNSET:
            self.encode_list_definitions(
                element, cast(dict[str, ListDefinition], document_tab.lists)
            )
        if document_tab.body is not UNSET:
            element.append(self.encode_body(cast(Body, document_tab.body)))
        self.encode_segments(element, "headers", "header", document_tab.headers)
        self.encode_segments(element, "footers", "footer", document_tab.footers)
        self.encode_segments(element, "footnotes", "footnote", document_tab.footnotes)
        return element

    def encode_document_style(self, style: DocumentStyle) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("document-style"))
        for value, name in (
            (style.document_mode, "document-mode"),
            (style.default_header_id, "default-header-id"),
            (style.default_footer_id, "default-footer-id"),
            (style.even_page_header_id, "even-page-header-id"),
            (style.even_page_footer_id, "even-page-footer-id"),
            (style.first_page_header_id, "first-page-header-id"),
            (style.first_page_footer_id, "first-page-footer-id"),
            (style.page_number_start, "page-number-start"),
        ):
            if value is not UNSET:
                element.set(gdocs_name(name), str(value))
        for value, name in (
            (style.use_even_page_header_footer, "use-even-page-header-footer"),
            (style.use_first_page_header_footer, "use-first-page-header-footer"),
            (
                style.use_custom_header_footer_margins,
                "use-custom-header-footer-margins",
            ),
            (style.flip_page_orientation, "flip-page-orientation"),
        ):
            self.encode_boolean_attribute(element, name, value)
        for value, name in (
            (style.page_width, "page-width"),
            (style.page_height, "page-height"),
            (style.margin_top, "margin-top"),
            (style.margin_bottom, "margin-bottom"),
            (style.margin_left, "margin-left"),
            (style.margin_right, "margin-right"),
            (style.margin_header, "margin-header"),
            (style.margin_footer, "margin-footer"),
        ):
            self.encode_point_attribute(element, name, value)
        if style.background_color is not UNSET:
            self.encode_optional_color(
                element, "background-color", cast(Color | None, style.background_color)
            )
        return element

    def encode_named_styles(self, styles: list[NamedStyle]) -> ElementTree.Element:
        wrapper = ElementTree.Element(gdocs_name("named-styles"))
        for style in styles:
            element = ElementTree.SubElement(wrapper, gdocs_name("named-style"))
            element.set(gdocs_name("named-style-type"), style.named_style_type)
            self.encode_metadata_text_style(element, style.text_style)
            if style.paragraph_style is not UNSET:
                paragraph = self.encode_paragraph_style(
                    cast(ParagraphStyle, style.paragraph_style),
                    include_named_style=True,
                )
                if paragraph is not None:
                    element.append(paragraph)
        return wrapper

    def encode_body(self, body: Body) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("body"))
        if not body.content or not isinstance(body.content[0], SectionBreak):
            raise ValueError("Body.content must begin with SectionBreak")
        current: ElementTree.Element | None = None
        section_content: list[StructuralElement] = []
        for node in body.content:
            if isinstance(node, SectionBreak):
                if current is not None:
                    current.extend(
                        self.encode_structural_sequence(section_content, body=True)
                    )
                current = ElementTree.SubElement(element, xhtml_name("section"))
                self.encode_section_style(current, node)
                section_content = []
            else:
                section_content.append(node)
        assert current is not None
        current.extend(self.encode_structural_sequence(section_content, body=True))
        return element

    def encode_list_definitions(
        self, parent: ElementTree.Element, definitions: dict[str, ListDefinition]
    ) -> None:
        wrapper = ElementTree.SubElement(parent, gdocs_name("list-definitions"))
        for list_id, definition in definitions.items():
            element = ElementTree.SubElement(wrapper, gdocs_name("list-definition"))
            element.set(gdocs_name("list-id"), list_id)
            for level in definition.levels:
                element.append(self.encode_list_level(level))

    def encode_list_level(self, level: ListLevel) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("list-level"))
        element.set(gdocs_name("glyph-format"), level.glyph_format)
        if level.glyph_type is not UNSET:
            element.set(gdocs_name("glyph-type"), cast(str, level.glyph_type))
        if level.glyph_symbol is not UNSET:
            element.set(gdocs_name("glyph-symbol"), cast(str, level.glyph_symbol))
        if level.alignment != "BULLET_ALIGNMENT_UNSPECIFIED":
            element.set(gdocs_name("alignment"), level.alignment)
        self.encode_point_attribute(
            element, "indent-first-line", level.indent_first_line
        )
        self.encode_point_attribute(element, "indent-start", level.indent_start)
        if level.start_number != 0:
            element.set(gdocs_name("start-number"), str(level.start_number))
        self.encode_metadata_text_style(element, level.text_style)
        return element

    def encode_metadata_text_style(
        self, element: ElementTree.Element, style: TextStyle | UnsetType
    ) -> None:
        if style is UNSET:
            return
        encoded = encode_text_style(element, style)
        if encoded is not element:
            encoded.remove(element)
            element.append(encoded)

    def encode_section_style(
        self, section: ElementTree.Element, section_break: SectionBreak
    ) -> None:
        style = section_break.style
        element = ElementTree.SubElement(section, gdocs_name("section-style"))
        scalar_fields = (
            (style.column_separator_style, "column-separator-style"),
            (style.content_direction, "content-direction"),
            (style.section_type, "section-type"),
            (style.default_header_id, "default-header-id"),
            (style.default_footer_id, "default-footer-id"),
            (style.even_page_header_id, "even-page-header-id"),
            (style.even_page_footer_id, "even-page-footer-id"),
            (style.first_page_header_id, "first-page-header-id"),
            (style.first_page_footer_id, "first-page-footer-id"),
            (style.page_number_start, "page-number-start"),
        )
        for value, name in scalar_fields:
            if value is not UNSET:
                element.set(gdocs_name(name), str(value))
        self.encode_boolean_attribute(
            element, "use-first-page-header-footer", style.use_first_page_header_footer
        )
        self.encode_boolean_attribute(
            element, "flip-page-orientation", style.flip_page_orientation
        )
        for value, name in (
            (style.margin_top, "margin-top"),
            (style.margin_bottom, "margin-bottom"),
            (style.margin_left, "margin-left"),
            (style.margin_right, "margin-right"),
            (style.margin_header, "margin-header"),
            (style.margin_footer, "margin-footer"),
        ):
            self.encode_point_attribute(element, name, value)
        if style.columns is not UNSET:
            columns = ElementTree.SubElement(element, gdocs_name("columns"))
            for column in cast(list[SectionColumn], style.columns):
                child = ElementTree.SubElement(columns, gdocs_name("column"))
                self.encode_point_attribute(child, "width", column.width)
                self.encode_point_attribute(child, "padding-end", column.padding_end)

    def encode_boolean_attribute(
        self, element: ElementTree.Element, name: str, value: bool | UnsetType
    ) -> None:
        if value is not UNSET:
            element.set(gdocs_name(name), "true" if value else "false")

    def encode_point_attribute(
        self,
        element: ElementTree.Element,
        name: str,
        value: Dimension | UnsetType,
    ) -> None:
        if value is not UNSET:
            element.set(
                gdocs_name(name), format_number(cast(Dimension, value).magnitude)
            )

    def encode_optional_color(
        self, parent: ElementTree.Element, name: str, color: Color | None
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        if color is None:
            element.set(gdocs_name("transparent"), "true")
        else:
            element.set(gdocs_name("red"), format_number(color.red))
            element.set(gdocs_name("green"), format_number(color.green))
            element.set(gdocs_name("blue"), format_number(color.blue))

    def encode_segments(
        self,
        document_tab: ElementTree.Element,
        wrapper_name: str,
        item_name: str,
        segments: dict[str, Segment] | UnsetType,
    ) -> None:
        if segments is UNSET:
            return
        decoded_segments = cast(dict[str, Segment], segments)
        wrapper = ElementTree.SubElement(document_tab, gdocs_name(wrapper_name))
        for key, segment in decoded_segments.items():
            item = ElementTree.SubElement(wrapper, gdocs_name(item_name))
            item.set(gdocs_name("key"), key)
            item.set(gdocs_name("segment-id"), segment.segment_id)
            item.extend(self.encode_structural_sequence(segment.content))

    def encode_structural_sequence(
        self, elements: list[StructuralElement], body: bool = False
    ) -> list[ElementTree.Element]:
        encoded: list[ElementTree.Element] = []
        index = 0
        while index < len(elements):
            element = elements[index]
            if isinstance(element, SectionBreak):
                if body:
                    raise ValueError("SectionBreak must be projected as a section")
                raise ValueError("SectionBreak is only valid in a body")
            if isinstance(element, Paragraph):
                key = self.bullet_group_key(element)
                if key is None:
                    encoded.append(self.encode_paragraph(element))
                else:
                    end = index + 1
                    while end < len(elements):
                        candidate = elements[end]
                        if not isinstance(candidate, Paragraph):
                            break
                        if self.bullet_group_key(candidate) != key:
                            break
                        end += 1
                    encoded.append(self.encode_list(elements[index:end], key))  # type: ignore[arg-type]
                    index = end
                    continue
            elif isinstance(element, Table):
                encoded.append(self.encode_table(element))
            elif isinstance(element, TableOfContents):
                table_of_contents = ElementTree.Element(gdocs_name("table-of-contents"))
                table_of_contents.extend(
                    self.encode_structural_sequence(element.content, body=False)
                )
                encoded.append(table_of_contents)
            else:
                raise ValueError(
                    f"unsupported structural element {type(element).__name__}"
                )
            index += 1
        return encoded

    def bullet_group_key(self, paragraph: Paragraph) -> tuple[str, str] | None:
        bullet = paragraph.bullet
        if isinstance(bullet, Bullet):
            return ("existing", bullet.list_id)
        if isinstance(bullet, BulletPreset):
            return ("preset", bullet.preset)
        if bullet is UNSET:
            return None
        raise ValueError(f"unsupported paragraph bullet object {type(bullet).__name__}")

    def encode_list(
        self, paragraphs: list[Paragraph], key: tuple[str, str]
    ) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("list"))
        kind, identity = key
        element.set(
            gdocs_name("list-id" if kind == "existing" else "bullet-preset"), identity
        )
        for paragraph in paragraphs:
            item = ElementTree.SubElement(element, xhtml_name("li"))
            bullet = paragraph.bullet
            assert isinstance(bullet, (Bullet, BulletPreset))
            if bullet.nesting_level != 0:
                item.set(gdocs_name("nesting-level"), str(bullet.nesting_level))
            if isinstance(bullet, Bullet) and bullet.text_style is not UNSET:
                metadata = ElementTree.Element(gdocs_name("bullet-style"))
                self.encode_metadata_text_style(metadata, bullet.text_style)
                if metadata.attrib or list(metadata):
                    item.append(metadata)
            item.append(self.encode_paragraph(paragraph))
        return element

    def encode_table(self, table: Table) -> ElementTree.Element:
        element = ElementTree.Element(xhtml_name("table"))
        if table.table_key is not None:
            element.set(gdocs_name("table-key"), table.table_key)
        if table.column_styles is not UNSET:
            colgroup = ElementTree.SubElement(element, xhtml_name("colgroup"))
            for column in cast(list[TableColumn], table.column_styles):
                child = ElementTree.SubElement(colgroup, xhtml_name("col"))
                child.set(gdocs_name("width-type"), column.width_type)
                self.encode_point_attribute(child, "width", column.width)
        tbody = ElementTree.SubElement(element, xhtml_name("tbody"))
        for row in table.rows:
            tbody.append(self.encode_table_row(row))
        return element

    def encode_table_row(self, row: TableRow) -> ElementTree.Element:
        element = ElementTree.Element(xhtml_name("tr"))
        if row.row_key is not None:
            element.set(gdocs_name("row-key"), row.row_key)
        self.encode_point_attribute(element, "min-height", row.min_height)
        self.encode_boolean_attribute(element, "prevent-overflow", row.prevent_overflow)
        self.encode_boolean_attribute(element, "is-header", row.is_header)
        for cell in row.cells:
            element.append(self.encode_table_cell(cell))
        return element

    def encode_table_cell(self, cell: TableCell) -> ElementTree.Element:
        element = ElementTree.Element(xhtml_name("td"))
        if cell.cell_key is not None:
            element.set(gdocs_name("cell-key"), cell.cell_key)
        if cell.style is not UNSET:
            style = cast(TableCellStyle, cell.style)
            if style.row_span != 1:
                element.set("rowspan", str(style.row_span))
            if style.column_span != 1:
                element.set("colspan", str(style.column_span))
            metadata = self.encode_table_cell_style(style)
            if metadata is not None:
                element.append(metadata)
        element.extend(self.encode_structural_sequence(cell.content, body=False))
        return element

    def encode_table_cell_style(
        self, style: TableCellStyle
    ) -> ElementTree.Element | None:
        element = ElementTree.Element(gdocs_name("cell-style"))
        if style.content_alignment is not UNSET:
            element.set(
                gdocs_name("content-alignment"), cast(str, style.content_alignment)
            )
        for value, name in (
            (style.padding_left, "padding-left"),
            (style.padding_right, "padding-right"),
            (style.padding_top, "padding-top"),
            (style.padding_bottom, "padding-bottom"),
        ):
            self.encode_point_attribute(element, name, value)
        if style.background_color is not UNSET:
            self.encode_optional_color(
                element, "background-color", cast(Color | None, style.background_color)
            )
        for value, name in (
            (style.border_left, "border-left"),
            (style.border_right, "border-right"),
            (style.border_top, "border-top"),
            (style.border_bottom, "border-bottom"),
        ):
            if value is not UNSET:
                self.encode_table_cell_border(
                    element, name, cast(TableCellBorder, value)
                )
        return element if element.attrib or list(element) else None

    def encode_table_cell_border(
        self, parent: ElementTree.Element, name: str, border: TableCellBorder
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        element.set(gdocs_name("dash-style"), border.dash_style)
        self.encode_point_attribute(element, "width", border.width)
        self.encode_optional_color(element, "color", border.color)

    def encode_paragraph(self, paragraph: Paragraph) -> ElementTree.Element:
        tag = gdocs_name("paragraph")
        style: ParagraphStyle | None = None
        if paragraph.style is not UNSET:
            style = cast(ParagraphStyle, paragraph.style)
            if style.named_style_type is not UNSET:
                tag = _PARAGRAPH_TAGS[cast(str, style.named_style_type)]
        element = ElementTree.Element(tag)
        if style is not None:
            metadata = self.encode_paragraph_style(style, include_named_style=False)
            if metadata is not None:
                element.append(metadata)
        if paragraph.positioned_object_ids is not UNSET:
            wrapper = ElementTree.SubElement(element, gdocs_name("positioned-objects"))
            for object_id in cast(list[str], paragraph.positioned_object_ids):
                item = ElementTree.SubElement(wrapper, gdocs_name("positioned-object"))
                item.set(gdocs_name("id"), object_id)
        for item in paragraph.elements:
            element.append(self.encode_paragraph_element(item))
        return element

    def encode_paragraph_element(self, item: ParagraphElement) -> ElementTree.Element:
        if isinstance(item, TextRun):
            return self.encode_text_run(item)
        if isinstance(item, AutoText):
            element = ElementTree.Element(gdocs_name("auto-text"))
            element.set(gdocs_name("type"), item.auto_text_type)
        elif isinstance(item, ColumnBreak):
            element = ElementTree.Element(gdocs_name("column-break"))
        elif isinstance(item, DateElement):
            element = ElementTree.Element(xhtml_name("time"))
            element.set(gdocs_name("date-id"), item.date_id)
            for value, name in (
                (item.date_format, gdocs_name("date-format")),
                (item.display_text, gdocs_name("display-text")),
                (item.locale, gdocs_name("locale")),
                (item.time_format, gdocs_name("time-format")),
                (item.time_zone_id, gdocs_name("time-zone-id")),
                (item.timestamp, "datetime"),
            ):
                if value is not UNSET:
                    element.set(name, cast(str, value))
        elif isinstance(item, Equation):
            return ElementTree.Element(gdocs_name("equation"))
        elif isinstance(item, FootnoteReference):
            element = ElementTree.Element(gdocs_name("footnote-reference"))
            element.set(gdocs_name("footnote-id"), item.footnote_id)
            element.set(gdocs_name("footnote-number"), item.footnote_number)
        elif isinstance(item, HorizontalRule):
            element = ElementTree.Element(xhtml_name("hr"))
        elif isinstance(item, InlineObjectReference):
            element = ElementTree.Element(gdocs_name("inline-object"))
            element.set(gdocs_name("inline-object-id"), item.inline_object_id)
        elif isinstance(item, PageBreak):
            element = ElementTree.Element(gdocs_name("page-break"))
        elif isinstance(item, PersonReference):
            element = ElementTree.Element(gdocs_name("person"))
            element.set(gdocs_name("person-id"), item.person_id)
            if item.email is not UNSET:
                element.set(gdocs_name("email"), cast(str, item.email))
            if item.name is not UNSET:
                element.set(gdocs_name("name"), cast(str, item.name))
        elif isinstance(item, RichLink):
            element = ElementTree.Element(gdocs_name("rich-link"))
            element.set(gdocs_name("rich-link-id"), item.rich_link_id)
            element.set(gdocs_name("uri"), item.uri)
            if item.title is not UNSET:
                element.set(gdocs_name("title"), cast(str, item.title))
            if item.mime_type is not UNSET:
                element.set(gdocs_name("mime-type"), cast(str, item.mime_type))
        else:
            raise ValueError(f"unsupported paragraph element {type(item).__name__}")
        return encode_text_style(element, item.text_style)

    def encode_paragraph_style(
        self, style: ParagraphStyle, *, include_named_style: bool = True
    ) -> ElementTree.Element | None:
        element = ElementTree.Element(gdocs_name("paragraph-style"))
        scalar_fields = (
            (style.alignment, "alignment"),
            (style.direction, "direction"),
            (style.line_spacing, "line-spacing"),
            (style.spacing_mode, "spacing-mode"),
            (style.heading_id, "heading-id"),
        )
        if include_named_style and style.named_style_type is not UNSET:
            element.set(
                gdocs_name("named-style-type"), cast(str, style.named_style_type)
            )
        for value, name in scalar_fields:
            if value is not UNSET:
                element.set(
                    gdocs_name(name),
                    format_number(value) if isinstance(value, float) else str(value),
                )
        for value, name in (
            (style.space_above, "space-above"),
            (style.space_below, "space-below"),
            (style.indent_first_line, "indent-first-line"),
            (style.indent_start, "indent-start"),
            (style.indent_end, "indent-end"),
        ):
            self.encode_point_attribute(element, name, value)
        for value, name in (
            (style.keep_lines_together, "keep-lines-together"),
            (style.keep_with_next, "keep-with-next"),
            (style.avoid_widow_and_orphan, "avoid-widow-and-orphan"),
            (style.page_break_before, "page-break-before"),
        ):
            self.encode_boolean_attribute(element, name, value)
        for value, name in (
            (style.border_between, "border-between"),
            (style.border_top, "border-top"),
            (style.border_bottom, "border-bottom"),
            (style.border_left, "border-left"),
            (style.border_right, "border-right"),
        ):
            if value is not UNSET:
                self.encode_paragraph_border(
                    element, name, cast(ParagraphBorder, value)
                )
        if style.shading_color is not UNSET:
            self.encode_optional_color(
                element,
                "shading-color",
                cast(Color | None, style.shading_color),
            )
        if style.tab_stops is not UNSET:
            wrapper = ElementTree.SubElement(element, gdocs_name("tab-stops"))
            for stop in cast(list[TabStop], style.tab_stops):
                child = ElementTree.SubElement(wrapper, gdocs_name("tab-stop"))
                child.set(gdocs_name("alignment"), stop.alignment)
                self.encode_point_attribute(child, "offset", stop.offset)
        return element if element.attrib or list(element) else None

    def encode_paragraph_border(
        self, parent: ElementTree.Element, name: str, border: ParagraphBorder
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        element.set(gdocs_name("dash-style"), border.dash_style)
        self.encode_point_attribute(element, "width", border.width)
        self.encode_point_attribute(element, "padding", border.padding)
        self.encode_optional_color(element, "color", border.color)

    def encode_text_run(self, run: TextRun) -> ElementTree.Element:
        span = ElementTree.Element(xhtml_name("span"))
        parts = run.content.split("\n")
        span.text = parts[0]
        for part in parts[1:]:
            br = ElementTree.SubElement(span, xhtml_name("br"))
            br.tail = part
        return encode_text_style(span, run.text_style)


def serialize_document(document: Document) -> str:
    ElementTree.register_namespace("", XHTML_NAMESPACE)
    ElementTree.register_namespace("g", GDOCS_NAMESPACE)
    root = _Encoder().encode_document(document)
    _indent_xml(root)
    xml = ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)
    return f"{XML_DECLARATION}\n{xml}\n"
