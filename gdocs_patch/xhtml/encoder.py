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
    MAX_ELEMENT_DEPTH,
    MAX_XHTML_CHARACTERS,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    XHTMLParseError,
    _indent_xml,  # pyright: ignore[reportPrivateUsage]
    encode_text_style,
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

_DOCUMENT_MODES = {"DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"}
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
_SECTION_SEPARATOR_STYLES = {
    "COLUMN_SEPARATOR_STYLE_UNSPECIFIED",
    "NONE",
    "BETWEEN_EACH_COLUMN",
}
_DIRECTIONS = {"CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"}
_SECTION_TYPES = {"SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"}
_GLYPH_TYPES = {
    "GLYPH_TYPE_UNSPECIFIED",
    "NONE",
    "DECIMAL",
    "ZERO_DECIMAL",
    "UPPER_ALPHA",
    "ALPHA",
    "UPPER_ROMAN",
    "ROMAN",
}
_BULLET_ALIGNMENTS = {"BULLET_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"}
_CONTENT_ALIGNMENTS = {
    "CONTENT_ALIGNMENT_UNSPECIFIED",
    "CONTENT_ALIGNMENT_UNSUPPORTED",
    "TOP",
    "MIDDLE",
    "BOTTOM",
}
_WIDTH_TYPES = {"WIDTH_TYPE_UNSPECIFIED", "EVENLY_DISTRIBUTED", "FIXED_WIDTH"}
_DASH_STYLES = {"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"}
_ALIGNMENTS = {"ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END", "JUSTIFIED"}
_SPACING_MODES = {"SPACING_MODE_UNSPECIFIED", "NEVER_COLLAPSE", "COLLAPSE_LISTS"}
_TAB_ALIGNMENTS = {"TAB_STOP_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"}
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

_SUGGESTIONS_VIEW_MODES = {
    "DEFAULT_FOR_CURRENT_ACCESS",
    "SUGGESTIONS_INLINE",
    "PREVIEW_SUGGESTIONS_ACCEPTED",
    "PREVIEW_WITHOUT_SUGGESTIONS",
}

_PARAGRAPH_TAGS = {
    "NAMED_STYLE_TYPE_UNSPECIFIED": gdocs_name("named-style-unspecified"),
    "NORMAL_TEXT": xhtml_name("p"),
    "TITLE": gdocs_name("title"),
    "SUBTITLE": gdocs_name("subtitle"),
    **{f"HEADING_{level}": xhtml_name(f"h{level}") for level in range(1, 7)},
}


class _Encoder:
    def encode_document(self, document: Document) -> ElementTree.Element:
        if not isinstance(document, Document):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("document must be a Document")
        root = ElementTree.Element(xhtml_name("html"))
        root.set(
            gdocs_name("document-id"),
            require_string(document.document_id, "Document.document_id"),
        )
        root.set(gdocs_name("title"), require_string(document.title, "Document.title"))
        if document.revision_id is not UNSET:
            root.set(
                gdocs_name("revision-id"),
                require_string(document.revision_id, "Document.revision_id"),
            )
        if document.suggestions_view_mode is not UNSET:
            root.set(
                gdocs_name("suggestions-view-mode"),
                require_enum(
                    document.suggestions_view_mode,
                    _SUGGESTIONS_VIEW_MODES,
                    "Document.suggestions_view_mode",
                ),
            )

        require_list(document.tabs, "Document.tabs")
        body = ElementTree.SubElement(root, xhtml_name("body"))
        for tab in document.tabs:
            body.append(self.encode_tab(tab))
        return root

    def encode_tab(self, tab: Tab) -> ElementTree.Element:
        if not isinstance(tab, Tab):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise ValueError("Document.tabs entries must be Tab objects")
        element = ElementTree.Element(gdocs_name("tab"))
        element.set(gdocs_name("tab-id"), require_string(tab.tab_id, "Tab.tab_id"))
        element.set(gdocs_name("title"), require_string(tab.title, "Tab.title"))
        element.set(gdocs_name("index"), str(require_integer(tab.index, "Tab.index")))
        nesting_level = require_integer(tab.nesting_level, "Tab.nesting_level")
        if nesting_level != 0:
            element.set(gdocs_name("nesting-level"), str(nesting_level))
        if tab.parent_tab_id is not UNSET:
            element.set(
                gdocs_name("parent-tab-id"),
                require_string(tab.parent_tab_id, "Tab.parent_tab_id"),
            )
        if tab.icon_emoji is not UNSET:
            element.set(
                gdocs_name("icon-emoji"),
                require_string(tab.icon_emoji, "Tab.icon_emoji"),
            )

        if tab.content is not UNSET:
            if not isinstance(tab.content, DocumentTab):
                raise ValueError("Tab.content must be a DocumentTab or UNSET")
            element.append(self.encode_document_tab(tab.content))
        require_list(tab.children, "Tab.children")
        if tab.children:
            child_tabs = ElementTree.SubElement(element, gdocs_name("child-tabs"))
            for child in tab.children:
                child_tabs.append(self.encode_tab(child))
        return element

    def encode_document_tab(self, document_tab: DocumentTab) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("document-tab"))
        if document_tab.named_styles is not UNSET:
            require_list(document_tab.named_styles, "DocumentTab.named_styles")
        if document_tab.lists is not UNSET:
            require_dict(document_tab.lists, "DocumentTab.lists")
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
        if style.document_mode is not UNSET:
            element.set(
                gdocs_name("document-mode"),
                require_enum(
                    style.document_mode, _DOCUMENT_MODES, "DocumentStyle.document_mode"
                ),
            )
        for value, name in (
            (style.default_header_id, "default-header-id"),
            (style.default_footer_id, "default-footer-id"),
            (style.even_page_header_id, "even-page-header-id"),
            (style.even_page_footer_id, "even-page-footer-id"),
            (style.first_page_header_id, "first-page-header-id"),
            (style.first_page_footer_id, "first-page-footer-id"),
        ):
            if value is not UNSET:
                element.set(
                    gdocs_name(name), require_string(value, f"DocumentStyle.{name}")
                )
        if style.page_number_start is not UNSET:
            element.set(
                gdocs_name("page-number-start"),
                str(
                    require_integer(
                        style.page_number_start, "DocumentStyle.page_number_start"
                    )
                ),
            )
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
        require_list(styles, "DocumentTab.named_styles")
        wrapper = ElementTree.Element(gdocs_name("named-styles"))
        for style in styles:
            element = ElementTree.SubElement(wrapper, gdocs_name("named-style"))
            element.set(
                gdocs_name("type"),
                require_enum(
                    style.named_style_type,
                    _NAMED_STYLE_TYPES,
                    "NamedStyle.named_style_type",
                ),
            )
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
        require_list(body.content, "Body.content")
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
        require_dict(definitions, "DocumentTab.lists")
        wrapper = ElementTree.SubElement(parent, gdocs_name("list-definitions"))
        for list_id, definition in definitions.items():
            require_list(definition.levels, "ListDefinition.levels")
            element = ElementTree.SubElement(wrapper, gdocs_name("list-definition"))
            element.set(
                gdocs_name("list-id"),
                require_string(list_id, "DocumentTab.lists key"),
            )
            for level in definition.levels:
                element.append(self.encode_list_level(level))

    def encode_list_level(self, level: ListLevel) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("list-level"))
        element.set(
            gdocs_name("glyph-format"),
            require_string(level.glyph_format, "ListLevel.glyph_format"),
        )
        if level.glyph_type is not UNSET:
            element.set(
                gdocs_name("glyph-type"),
                require_enum(level.glyph_type, _GLYPH_TYPES, "ListLevel.glyph_type"),
            )
        if level.glyph_symbol is not UNSET:
            element.set(
                gdocs_name("glyph-symbol"),
                require_string(level.glyph_symbol, "ListLevel.glyph_symbol"),
            )
        alignment = require_enum(
            level.alignment, _BULLET_ALIGNMENTS, "ListLevel.alignment"
        )
        if alignment != "BULLET_ALIGNMENT_UNSPECIFIED":
            element.set(gdocs_name("alignment"), alignment)
        self.encode_point_attribute(
            element, "indent-first-line", level.indent_first_line
        )
        self.encode_point_attribute(element, "indent-start", level.indent_start)
        start_number = require_integer(level.start_number, "ListLevel.start_number")
        if start_number != 0:
            element.set(gdocs_name("start-number"), str(start_number))
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
        for value, name, allowed in (
            (
                style.column_separator_style,
                "column-separator-style",
                _SECTION_SEPARATOR_STYLES,
            ),
            (style.content_direction, "content-direction", _DIRECTIONS),
            (style.section_type, "section-type", _SECTION_TYPES),
        ):
            if value is not UNSET:
                element.set(
                    gdocs_name(name),
                    require_enum(value, allowed, f"SectionStyle.{name}"),
                )
        for value, name in (
            (style.default_header_id, "default-header-id"),
            (style.default_footer_id, "default-footer-id"),
            (style.even_page_header_id, "even-page-header-id"),
            (style.even_page_footer_id, "even-page-footer-id"),
            (style.first_page_header_id, "first-page-header-id"),
            (style.first_page_footer_id, "first-page-footer-id"),
        ):
            if value is not UNSET:
                element.set(
                    gdocs_name(name), require_string(value, f"SectionStyle.{name}")
                )
        if style.page_number_start is not UNSET:
            element.set(
                gdocs_name("page-number-start"),
                str(
                    require_integer(
                        style.page_number_start, "SectionStyle.page_number_start"
                    )
                ),
            )
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
            require_list(style.columns, "SectionStyle.columns")
            columns = ElementTree.SubElement(element, gdocs_name("columns"))
            for column in cast(list[SectionColumn], style.columns):
                child = ElementTree.SubElement(columns, gdocs_name("column"))
                self.encode_point_attribute(child, "width", column.width)
                self.encode_point_attribute(child, "padding-end", column.padding_end)

    def encode_boolean_attribute(
        self, element: ElementTree.Element, name: str, value: bool | UnsetType
    ) -> None:
        if value is not UNSET:
            boolean = require_boolean(value, name)
            element.set(gdocs_name(name), "true" if boolean else "false")

    def encode_point_attribute(
        self,
        element: ElementTree.Element,
        name: str,
        value: Dimension | UnsetType,
    ) -> None:
        if value is not UNSET:
            if not isinstance(value, Dimension):
                raise ValueError(f"{name} must be a Dimension")
            element.set(
                gdocs_name(name),
                format_number(require_number(value.magnitude, f"{name}.magnitude")),
            )

    def encode_optional_color(
        self, parent: ElementTree.Element, name: str, color: Color | None
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        if color is None:
            element.set(gdocs_name("transparent"), "true")
        else:
            if not isinstance(color, Color):  # pyright: ignore[reportUnnecessaryIsInstance]
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
        document_tab: ElementTree.Element,
        wrapper_name: str,
        item_name: str,
        segments: dict[str, Segment] | UnsetType,
    ) -> None:
        if segments is UNSET:
            return
        require_dict(segments, f"DocumentTab.{wrapper_name}")
        decoded_segments = cast(dict[str, Segment], segments)
        wrapper = ElementTree.SubElement(document_tab, gdocs_name(wrapper_name))
        for key, segment in decoded_segments.items():
            item = ElementTree.SubElement(wrapper, gdocs_name(item_name))
            item.set(
                gdocs_name("key"),
                require_string(key, f"DocumentTab.{wrapper_name} key"),
            )
            item.set(
                gdocs_name("segment-id"),
                require_string(segment.segment_id, "Segment.segment_id"),
            )
            require_list(segment.content, "Segment.content")
            item.extend(self.encode_structural_sequence(segment.content))

    def encode_structural_sequence(
        self, elements: list[StructuralElement], body: bool = False
    ) -> list[ElementTree.Element]:
        require_list(elements, "structural content")
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
            return ("existing", require_string(bullet.list_id, "Bullet.list_id"))
        if isinstance(bullet, BulletPreset):
            return (
                "preset",
                require_enum(bullet.preset, _BULLET_PRESETS, "BulletPreset.preset"),
            )
        if bullet is UNSET:
            return None
        raise ValueError(f"unsupported paragraph bullet object {type(bullet).__name__}")

    def encode_list(
        self, paragraphs: list[Paragraph], key: tuple[str, str]
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
            assert isinstance(bullet, (Bullet, BulletPreset))
            nesting_level = require_integer(
                bullet.nesting_level, f"{type(bullet).__name__}.nesting_level"
            )
            if nesting_level != 0:
                item.set(gdocs_name("nesting-level"), str(nesting_level))
            if isinstance(bullet, Bullet) and bullet.text_style is not UNSET:
                metadata = ElementTree.Element(gdocs_name("bullet-style"))
                self.encode_metadata_text_style(metadata, bullet.text_style)
                if metadata.attrib or list(metadata):
                    item.append(metadata)
            item.append(self.encode_paragraph(paragraph))
        return element

    def encode_table(self, table: Table) -> ElementTree.Element:
        require_list(table.rows, "Table.rows")
        element = ElementTree.Element(xhtml_name("table"))
        if table.table_key is not None:
            element.set(
                gdocs_name("table-key"),
                require_string(table.table_key, "Table.table_key"),
            )
        if table.column_styles is not UNSET:
            require_list(table.column_styles, "Table.column_styles")
            colgroup = ElementTree.SubElement(element, xhtml_name("colgroup"))
            for column in cast(list[TableColumn], table.column_styles):
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

    def encode_table_row(self, row: TableRow) -> ElementTree.Element:
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

    def encode_table_cell(self, cell: TableCell) -> ElementTree.Element:
        require_list(cell.content, "TableCell.content")
        element = ElementTree.Element(xhtml_name("td"))
        if cell.cell_key is not None:
            element.set(
                gdocs_name("cell-key"),
                require_string(cell.cell_key, "TableCell.cell_key"),
            )
        if cell.style is not UNSET:
            style = cast(TableCellStyle, cell.style)
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
        element.extend(self.encode_structural_sequence(cell.content, body=False))
        return element

    def encode_table_cell_style(
        self, style: TableCellStyle
    ) -> ElementTree.Element | None:
        element = ElementTree.Element(gdocs_name("cell-style"))
        if style.content_alignment is not UNSET:
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
        element.set(
            gdocs_name("dash-style"),
            require_enum(border.dash_style, _DASH_STYLES, "TableCellBorder.dash_style"),
        )
        self.encode_point_attribute(element, "width", border.width)
        self.encode_optional_color(element, "color", border.color)

    def encode_paragraph(self, paragraph: Paragraph) -> ElementTree.Element:
        tag = gdocs_name("paragraph")
        style: ParagraphStyle | None = None
        if paragraph.style is not UNSET:
            style = cast(ParagraphStyle, paragraph.style)
            if style.named_style_type is not UNSET:
                named_style_type = require_enum(
                    style.named_style_type,
                    _NAMED_STYLE_TYPES,
                    "ParagraphStyle.named_style_type",
                )
                tag = _PARAGRAPH_TAGS[named_style_type]
        element = ElementTree.Element(tag)
        if style is not None:
            metadata = self.encode_paragraph_style(style, include_named_style=False)
            if metadata is not None:
                element.append(metadata)
        if paragraph.positioned_object_ids is not UNSET:
            require_list(
                paragraph.positioned_object_ids, "Paragraph.positioned_object_ids"
            )
            wrapper = ElementTree.SubElement(element, gdocs_name("positioned-objects"))
            for object_id in cast(list[str], paragraph.positioned_object_ids):
                item = ElementTree.SubElement(wrapper, gdocs_name("positioned-object"))
                item.set(
                    gdocs_name("id"),
                    require_string(object_id, "Paragraph.positioned_object_ids entry"),
                )
        require_list(paragraph.elements, "Paragraph.elements")
        for item in paragraph.elements:
            element.append(self.encode_paragraph_element(item))
        return element

    def encode_paragraph_element(self, item: ParagraphElement) -> ElementTree.Element:
        if isinstance(item, TextRun):
            return self.encode_text_run(item)
        if isinstance(item, AutoText):
            element = ElementTree.Element(gdocs_name("auto-text"))
            element.set(
                gdocs_name("type"),
                require_enum(
                    item.auto_text_type, _AUTO_TEXT_TYPES, "AutoText.auto_text_type"
                ),
            )
        elif isinstance(item, ColumnBreak):
            element = ElementTree.Element(gdocs_name("column-break"))
        elif isinstance(item, DateElement):
            element = ElementTree.Element(xhtml_name("time"))
            element.set(
                gdocs_name("date-id"),
                require_string(item.date_id, "DateElement.date_id"),
            )
            if item.date_format is not UNSET:
                element.set(
                    gdocs_name("date-format"),
                    require_enum(
                        item.date_format, _DATE_FORMATS, "DateElement.date_format"
                    ),
                )
            if item.time_format is not UNSET:
                element.set(
                    gdocs_name("time-format"),
                    require_enum(
                        item.time_format, _TIME_FORMATS, "DateElement.time_format"
                    ),
                )
            for value, name, field in (
                (item.display_text, gdocs_name("display-text"), "display_text"),
                (item.locale, gdocs_name("locale"), "locale"),
                (item.time_zone_id, gdocs_name("time-zone-id"), "time_zone_id"),
                (item.timestamp, "datetime", "timestamp"),
            ):
                if value is not UNSET:
                    element.set(name, require_string(value, f"DateElement.{field}"))
        elif isinstance(item, Equation):
            return ElementTree.Element(gdocs_name("equation"))
        elif isinstance(item, FootnoteReference):
            element = ElementTree.Element(gdocs_name("footnote-reference"))
            element.set(
                gdocs_name("footnote-id"),
                require_string(item.footnote_id, "FootnoteReference.footnote_id"),
            )
            element.set(
                gdocs_name("footnote-number"),
                require_string(
                    item.footnote_number, "FootnoteReference.footnote_number"
                ),
            )
        elif isinstance(item, HorizontalRule):
            element = ElementTree.Element(xhtml_name("hr"))
        elif isinstance(item, InlineObjectReference):
            element = ElementTree.Element(gdocs_name("inline-object"))
            element.set(
                gdocs_name("inline-object-id"),
                require_string(
                    item.inline_object_id, "InlineObjectReference.inline_object_id"
                ),
            )
        elif isinstance(item, PageBreak):
            element = ElementTree.Element(gdocs_name("page-break"))
        elif isinstance(item, PersonReference):
            element = ElementTree.Element(gdocs_name("person"))
            element.set(
                gdocs_name("person-id"),
                require_string(item.person_id, "PersonReference.person_id"),
            )
            if item.email is not UNSET:
                element.set(
                    gdocs_name("email"),
                    require_string(item.email, "PersonReference.email"),
                )
            if item.name is not UNSET:
                element.set(
                    gdocs_name("name"),
                    require_string(item.name, "PersonReference.name"),
                )
        elif isinstance(item, RichLink):
            element = ElementTree.Element(gdocs_name("rich-link"))
            element.set(
                gdocs_name("rich-link-id"),
                require_string(item.rich_link_id, "RichLink.rich_link_id"),
            )
            element.set(gdocs_name("uri"), require_string(item.uri, "RichLink.uri"))
            if item.title is not UNSET:
                element.set(
                    gdocs_name("title"), require_string(item.title, "RichLink.title")
                )
            if item.mime_type is not UNSET:
                element.set(
                    gdocs_name("mime-type"),
                    require_string(item.mime_type, "RichLink.mime_type"),
                )
        else:
            raise ValueError(f"unsupported paragraph element {type(item).__name__}")
        return encode_text_style(element, item.text_style)

    def encode_paragraph_style(
        self, style: ParagraphStyle, *, include_named_style: bool = True
    ) -> ElementTree.Element | None:
        element = ElementTree.Element(gdocs_name("paragraph-style"))
        if include_named_style and style.named_style_type is not UNSET:
            element.set(
                gdocs_name("named-style-type"),
                require_enum(
                    style.named_style_type,
                    _NAMED_STYLE_TYPES,
                    "ParagraphStyle.named_style_type",
                ),
            )
        for value, name, allowed in (
            (style.alignment, "alignment", _ALIGNMENTS),
            (style.direction, "direction", _DIRECTIONS),
            (style.spacing_mode, "spacing-mode", _SPACING_MODES),
        ):
            if value is not UNSET:
                element.set(
                    gdocs_name(name),
                    require_enum(value, allowed, f"ParagraphStyle.{name}"),
                )
        if style.line_spacing is not UNSET:
            element.set(
                gdocs_name("line-spacing"),
                format_number(
                    require_number(style.line_spacing, "ParagraphStyle.line_spacing")
                ),
            )
        if style.heading_id is not UNSET:
            element.set(
                gdocs_name("heading-id"),
                require_string(style.heading_id, "ParagraphStyle.heading_id"),
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
            require_list(style.tab_stops, "ParagraphStyle.tab_stops")
            wrapper = ElementTree.SubElement(element, gdocs_name("tab-stops"))
            for stop in cast(list[TabStop], style.tab_stops):
                child = ElementTree.SubElement(wrapper, gdocs_name("tab-stop"))
                child.set(
                    gdocs_name("alignment"),
                    require_enum(stop.alignment, _TAB_ALIGNMENTS, "TabStop.alignment"),
                )
                self.encode_point_attribute(child, "offset", stop.offset)
        return element if element.attrib or list(element) else None

    def encode_paragraph_border(
        self, parent: ElementTree.Element, name: str, border: ParagraphBorder
    ) -> None:
        element = ElementTree.SubElement(parent, gdocs_name(name))
        element.set(
            gdocs_name("dash-style"),
            require_enum(border.dash_style, _DASH_STYLES, "ParagraphBorder.dash_style"),
        )
        self.encode_point_attribute(element, "width", border.width)
        self.encode_point_attribute(element, "padding", border.padding)
        self.encode_optional_color(element, "color", border.color)

    def encode_text_run(self, run: TextRun) -> ElementTree.Element:
        span = ElementTree.Element(xhtml_name("span"))
        parts = require_string(run.content, "TextRun.content").split("\n")
        span.text = parts[0]
        for part in parts[1:]:
            br = ElementTree.SubElement(span, xhtml_name("br"))
            br.tail = part
        return encode_text_style(span, run.text_style)


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
        _Decoder().decode_document(root)
    except XHTMLParseError as error:
        raise ValueError(
            f"document model cannot be encoded as valid XHTML: {error}"
        ) from error


def serialize_document(document: Document) -> str:
    ElementTree.register_namespace("", XHTML_NAMESPACE)
    ElementTree.register_namespace("g", GDOCS_NAMESPACE)
    try:
        root = _Encoder().encode_document(document)
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
