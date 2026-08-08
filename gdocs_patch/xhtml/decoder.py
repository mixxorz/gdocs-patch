import re
from dataclasses import dataclass
from typing import Any, Literal, Never, cast
from xml.etree import ElementTree
from xml.parsers import expat

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
    Link,
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
    SectionStyle,
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
    MAX_ELEMENT_DEPTH,
    MAX_XHTML_CHARACTERS,
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
from .tags import (
    BorderBetweenTag,
    BorderBottomTag,
    BorderLeftTag,
    BorderRightTag,
    BorderTopTag,
    BreakTag,
    ColorTag,
    NamedParagraphStyleTag,
    ParagraphBorderTag,
    ParagraphStyleTag,
    ParagraphTag,
    ShadingColorTag,
    SpanTag,
    TabStopsTag,
    TabStopTag,
)

_PARAGRAPH_TAGS = {
    gdocs_name("paragraph"): UNSET,
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
_TIME_FORMATS = {
    "TIME_FORMAT_UNSPECIFIED",
    "TIME_FORMAT_DISABLED",
    "TIME_FORMAT_HOUR_MINUTE",
    "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
}

_FORBIDDEN_XML_DECLARATION = re.compile(r"<!(?:DOCTYPE|ENTITY)\b")

_SUGGESTIONS_VIEW_MODES = {
    "DEFAULT_FOR_CURRENT_ACCESS",
    "SUGGESTIONS_INLINE",
    "PREVIEW_SUGGESTIONS_ACCEPTED",
    "PREVIEW_WITHOUT_SUGGESTIONS",
}


def _validate_no_children(element: ElementTree.Element, path: str) -> None:
    children = list(element)
    if children:
        parse_error(path, f"unknown child element {display_name(children[0].tag)}")


@dataclass
class _TableCellStyleFields:
    background_color: Color | None | UnsetType = UNSET
    border_left: TableCellBorder | UnsetType = UNSET
    border_right: TableCellBorder | UnsetType = UNSET
    border_top: TableCellBorder | UnsetType = UNSET
    border_bottom: TableCellBorder | UnsetType = UNSET
    padding_left: Dimension | UnsetType = UNSET
    padding_right: Dimension | UnsetType = UNSET
    padding_top: Dimension | UnsetType = UNSET
    padding_bottom: Dimension | UnsetType = UNSET
    content_alignment: (
        Literal[
            "CONTENT_ALIGNMENT_UNSPECIFIED",
            "CONTENT_ALIGNMENT_UNSUPPORTED",
            "TOP",
            "MIDDLE",
            "BOTTOM",
        ]
        | UnsetType
    ) = UNSET

    def has_values(self) -> bool:
        return any(
            value is not UNSET
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


SuggestionsViewMode = Literal[
    "DEFAULT_FOR_CURRENT_ACCESS",
    "SUGGESTIONS_INLINE",
    "PREVIEW_SUGGESTIONS_ACCEPTED",
    "PREVIEW_WITHOUT_SUGGESTIONS",
]


class _Decoder:
    def decode_tag[T: Tag](
        self, element: ElementTree.Element, tag_type: type[T], path: str
    ) -> T:
        try:
            return XHTMLDecoder().decode_element(element, tag_type)
        except DecodeError as error:
            error_path = path + "".join(f"/{display_name(name)}" for name in error.path)
            if error.attribute_name is not None:
                error_path += f"/@{display_name(error.attribute_name)}"
            message = str(error)
            if error.element_name is not None:
                message += f" {display_name(error.element_name)}"
            parse_error(error_path, message, cause=error)

    def decode_document(self, root: ElementTree.Element) -> Document:
        path = "/html"
        if root.tag != xhtml_name("html"):
            if root.tag.endswith("}html") or root.tag == "html":
                parse_error(path, "unsupported XHTML namespace")
            parse_error(path, "expected XHTML html root element")
        validate_attributes(
            root,
            {
                gdocs_name("document-id"),
                gdocs_name("title"),
                gdocs_name("revision-id"),
                gdocs_name("suggestions-view-mode"),
            },
            path,
        )
        document_id = required_string(root, gdocs_name("document-id"), path)
        title = required_string(root, gdocs_name("title"), path)
        revision_id = optional_string(root, gdocs_name("revision-id"))
        raw_mode = root.get(gdocs_name("suggestions-view-mode"))
        mode: SuggestionsViewMode | UnsetType
        if raw_mode is None:
            mode = UNSET
        else:
            mode = cast(
                "SuggestionsViewMode",
                parse_allowed(
                    raw_mode,
                    _SUGGESTIONS_VIEW_MODES,
                    f"{path}/@g:suggestions-view-mode",
                ),
            )

        validate_whitespace(root, path)
        children = list(root)
        body = extract_one_child(children, xhtml_name("body"), path, required=True)
        assert body is not None
        for child in children:
            if child is not body:
                parse_error(path, f"unknown child element {display_name(child.tag)}")

        return Document(
            document_id=document_id,
            title=title,
            revision_id=revision_id,
            suggestions_view_mode=mode,
            tabs=self.decode_tabs(body, f"{path}/body"),
        )

    def decode_tabs(self, body: ElementTree.Element, path: str) -> list[Tab]:
        validate_attributes(body, set(), path)
        validate_whitespace(body, path)
        tabs: list[Tab] = []
        for index, child in enumerate(body):
            if child.tag != gdocs_name("tab"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            tabs.append(self.decode_tab(child, f"{path}/g:tab[{index + 1}]"))
        return tabs

    def decode_tab(self, element: ElementTree.Element, path: str) -> Tab:
        validate_attributes(
            element,
            {
                gdocs_name("tab-id"),
                gdocs_name("title"),
                gdocs_name("index"),
                gdocs_name("nesting-level"),
                gdocs_name("parent-tab-id"),
                gdocs_name("icon-emoji"),
            },
            path,
        )
        tab_id = required_string(element, gdocs_name("tab-id"), path)
        title = required_string(element, gdocs_name("title"), path)
        index = parse_integer(
            required_string(element, gdocs_name("index"), path),
            f"{path}/@g:index",
        )
        raw_level = element.get(gdocs_name("nesting-level"))
        nesting_level = (
            0
            if raw_level is None
            else parse_integer(raw_level, f"{path}/@g:nesting-level")
        )
        parent_tab_id = optional_string(element, gdocs_name("parent-tab-id"))
        icon_emoji = optional_string(element, gdocs_name("icon-emoji"))

        validate_whitespace(element, path)
        children = list(element)
        document_tab = extract_one_child(children, gdocs_name("document-tab"), path)
        decoded_content = (
            UNSET
            if document_tab is None
            else self.decode_document_tab(document_tab, f"{path}/g:document-tab")
        )
        child_tabs = extract_one_child(children, gdocs_name("child-tabs"), path)
        decoded_children: list[Tab] = []
        if child_tabs is not None:
            child_path = f"{path}/g:child-tabs"
            validate_attributes(child_tabs, set(), child_path)
            validate_whitespace(child_tabs, child_path)
            for index, child in enumerate(child_tabs):
                if child.tag != gdocs_name("tab"):
                    parse_error(
                        child_path, f"unknown child element {display_name(child.tag)}"
                    )
                decoded_children.append(
                    self.decode_tab(child, f"{child_path}/g:tab[{index + 1}]")
                )
        for child in children:
            if child not in (document_tab, child_tabs):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        if nesting_level < 0:
            parse_error(
                f"{path}/@g:nesting-level", "nesting level must be non-negative"
            )
        return Tab(
            tab_id=tab_id,
            title=title,
            index=index,
            nesting_level=nesting_level,
            parent_tab_id=parent_tab_id,
            icon_emoji=icon_emoji,
            content=decoded_content,
            children=decoded_children,
        )

    def decode_document_tab(
        self, element: ElementTree.Element, path: str
    ) -> DocumentTab:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        children = list(element)
        body = extract_one_child(children, gdocs_name("body"), path)
        decoded_body = (
            UNSET if body is None else self.decode_body(body, f"{path}/g:body")
        )
        headers = extract_one_child(children, gdocs_name("headers"), path)
        decoded_headers = (
            UNSET
            if headers is None
            else self.decode_segments(headers, "header", f"{path}/g:headers")
        )
        footers = extract_one_child(children, gdocs_name("footers"), path)
        decoded_footers = (
            UNSET
            if footers is None
            else self.decode_segments(footers, "footer", f"{path}/g:footers")
        )
        footnotes = extract_one_child(children, gdocs_name("footnotes"), path)
        decoded_footnotes = (
            UNSET
            if footnotes is None
            else self.decode_segments(footnotes, "footnote", f"{path}/g:footnotes")
        )
        lists = extract_one_child(children, gdocs_name("list-definitions"), path)
        decoded_lists = (
            UNSET
            if lists is None
            else self.decode_list_definitions(lists, f"{path}/g:list-definitions")
        )
        document_style = extract_one_child(children, gdocs_name("document-style"), path)
        decoded_document_style = (
            UNSET
            if document_style is None
            else self.decode_document_style(document_style, f"{path}/g:document-style")
        )
        named_styles = extract_one_child(children, gdocs_name("named-styles"), path)
        decoded_named_styles = (
            UNSET
            if named_styles is None
            else self.decode_named_styles(named_styles, f"{path}/g:named-styles")
        )
        supported = {
            gdocs_name("body"),
            gdocs_name("headers"),
            gdocs_name("footers"),
            gdocs_name("footnotes"),
            gdocs_name("list-definitions"),
            gdocs_name("document-style"),
            gdocs_name("named-styles"),
        }
        for child in children:
            if child.tag not in supported:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return DocumentTab(
            body=decoded_body,
            headers=decoded_headers,
            footers=decoded_footers,
            footnotes=decoded_footnotes,
            lists=decoded_lists,
            document_style=decoded_document_style,
            named_styles=decoded_named_styles,
        )

    def decode_document_style(
        self, element: ElementTree.Element, path: str
    ) -> DocumentStyle:
        attribute_names = {
            "document-mode",
            "page-width",
            "page-height",
            "margin-top",
            "margin-bottom",
            "margin-left",
            "margin-right",
            "margin-header",
            "margin-footer",
            "default-header-id",
            "default-footer-id",
            "even-page-header-id",
            "even-page-footer-id",
            "first-page-header-id",
            "first-page-footer-id",
            "use-even-page-header-footer",
            "use-first-page-header-footer",
            "use-custom-header-footer-margins",
            "flip-page-orientation",
            "page-number-start",
        }
        validate_attributes(
            element, {gdocs_name(name) for name in attribute_names}, path
        )
        document_mode = self.optional_allowed(
            element,
            "document-mode",
            {"DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"},
            path,
        )
        page_width = self.optional_point(element, "page-width", path)
        page_height = self.optional_point(element, "page-height", path)
        margin_top = self.optional_point(element, "margin-top", path)
        margin_bottom = self.optional_point(element, "margin-bottom", path)
        margin_left = self.optional_point(element, "margin-left", path)
        margin_right = self.optional_point(element, "margin-right", path)
        margin_header = self.optional_point(element, "margin-header", path)
        margin_footer = self.optional_point(element, "margin-footer", path)
        default_header_id = optional_string(element, gdocs_name("default-header-id"))
        default_footer_id = optional_string(element, gdocs_name("default-footer-id"))
        even_page_header_id = optional_string(
            element, gdocs_name("even-page-header-id")
        )
        even_page_footer_id = optional_string(
            element, gdocs_name("even-page-footer-id")
        )
        first_page_header_id = optional_string(
            element, gdocs_name("first-page-header-id")
        )
        first_page_footer_id = optional_string(
            element, gdocs_name("first-page-footer-id")
        )
        use_even_page_header_footer = self.optional_boolean(
            element, "use-even-page-header-footer", path
        )
        use_first_page_header_footer = self.optional_boolean(
            element, "use-first-page-header-footer", path
        )
        use_custom_header_footer_margins = self.optional_boolean(
            element, "use-custom-header-footer-margins", path
        )
        flip_page_orientation = self.optional_boolean(
            element, "flip-page-orientation", path
        )
        page_number_start = self.optional_integer(element, "page-number-start", path)

        validate_whitespace(element, path)
        children = list(element)
        background = extract_one_child(children, gdocs_name("background-color"), path)
        background_color = (
            UNSET
            if background is None
            else self.decode_optional_color(background, f"{path}/g:background-color")
        )
        for child in children:
            if child is not background:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return DocumentStyle(
            background_color=background_color,
            document_mode=document_mode,  # type: ignore[arg-type]
            page_width=page_width,
            page_height=page_height,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            margin_left=margin_left,
            margin_right=margin_right,
            margin_header=margin_header,
            margin_footer=margin_footer,
            default_header_id=default_header_id,
            default_footer_id=default_footer_id,
            even_page_header_id=even_page_header_id,
            even_page_footer_id=even_page_footer_id,
            first_page_header_id=first_page_header_id,
            first_page_footer_id=first_page_footer_id,
            use_even_page_header_footer=use_even_page_header_footer,
            use_first_page_header_footer=use_first_page_header_footer,
            use_custom_header_footer_margins=use_custom_header_footer_margins,
            flip_page_orientation=flip_page_orientation,
            page_number_start=page_number_start,
        )

    def decode_named_styles(
        self, element: ElementTree.Element, path: str
    ) -> list[NamedStyle]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: list[NamedStyle] = []
        for index, child in enumerate(element):
            child_path = f"{path}/g:named-style[{index + 1}]"
            if child.tag != gdocs_name("named-style"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            validate_attributes(
                child,
                {gdocs_name("type")} | text_style_attributes(),
                child_path,
            )
            named_style_type = parse_allowed(
                required_string(child, gdocs_name("type"), child_path),
                _NAMED_STYLE_TYPES,
                f"{child_path}/@g:type",
            )
            construct_text_style = parse_text_style(child, child_path)

            validate_whitespace(child, child_path)
            children = list(child)
            anchor = extract_one_child(children, xhtml_name("a"), child_path)
            link: Link | UnsetType = UNSET
            if anchor is not None:
                anchor_path = f"{child_path}/a"
                link = decode_link(anchor, anchor_path)
                validate_whitespace(anchor, anchor_path)
                _validate_no_children(anchor, anchor_path)
            text_style = construct_text_style(link)
            paragraph = extract_one_child(
                children, gdocs_name("paragraph-style"), child_path
            )
            paragraph_style = (
                UNSET
                if paragraph is None
                else self._decode_paragraph_style_tag(
                    self.decode_tag(
                        paragraph,
                        NamedParagraphStyleTag,
                        f"{child_path}/g:paragraph-style",
                    ),
                    f"{child_path}/g:paragraph-style",
                )
            )
            for metadata in children:
                if metadata not in (anchor, paragraph):
                    parse_error(
                        child_path,
                        f"unknown child element {display_name(metadata.tag)}",
                    )
            result.append(
                NamedStyle(
                    named_style_type=named_style_type,  # type: ignore[arg-type]
                    text_style=text_style,
                    paragraph_style=paragraph_style,
                )
            )
        return result

    def decode_list_definitions(
        self, element: ElementTree.Element, path: str
    ) -> dict[str, ListDefinition]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: dict[str, ListDefinition] = {}
        for index, child in enumerate(element):
            child_path = f"{path}/g:list-definition[{index + 1}]"
            if child.tag != gdocs_name("list-definition"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            validate_attributes(child, {gdocs_name("list-id")}, child_path)
            list_id = required_string(child, gdocs_name("list-id"), child_path)
            validate_whitespace(child, child_path)
            if list_id in result:
                parse_error(child_path, f"duplicate list key {list_id!r}")
            levels: list[ListLevel] = []
            for level_index, level in enumerate(child):
                level_path = f"{child_path}/g:list-level[{level_index + 1}]"
                if level.tag != gdocs_name("list-level"):
                    parse_error(
                        child_path, f"unknown child element {display_name(level.tag)}"
                    )
                levels.append(self.decode_list_level(level, level_path))
            result[list_id] = ListDefinition(levels=levels)
        return result

    def decode_list_level(self, element: ElementTree.Element, path: str) -> ListLevel:
        scalar_names = {
            "glyph-format",
            "glyph-type",
            "glyph-symbol",
            "alignment",
            "indent-first-line",
            "indent-start",
            "start-number",
        }
        validate_attributes(
            element,
            {gdocs_name(name) for name in scalar_names} | text_style_attributes(),
            path,
        )
        glyph_type = element.get(gdocs_name("glyph-type"))
        glyph_symbol = element.get(gdocs_name("glyph-symbol"))
        if glyph_type is not None:
            glyph_type = parse_allowed(
                glyph_type, _GLYPH_TYPES, f"{path}/@g:glyph-type"
            )
        glyph_format = required_string(element, gdocs_name("glyph-format"), path)
        alignment = self.decode_default_allowed(
            element,
            "alignment",
            _BULLET_ALIGNMENTS,
            "BULLET_ALIGNMENT_UNSPECIFIED",
            path,
        )
        indent_first_line = self.optional_point(element, "indent-first-line", path)
        indent_start = self.optional_point(element, "indent-start", path)
        start_number = self.decode_default_integer(element, "start-number", 0, path)
        text_style = self.decode_metadata_text_style(element, path)
        if (glyph_type is None) == (glyph_symbol is None):
            parse_error(
                path, "exactly one of g:glyph-type and g:glyph-symbol is required"
            )
        return construct_model(
            path,
            lambda: ListLevel(
                glyph_format=glyph_format,
                glyph_type=UNSET if glyph_type is None else glyph_type,  # type: ignore[arg-type]
                glyph_symbol=UNSET if glyph_symbol is None else glyph_symbol,
                alignment=alignment,  # type: ignore[arg-type]
                indent_first_line=indent_first_line,
                indent_start=indent_start,
                start_number=start_number,
                text_style=text_style,
            ),
        )

    def decode_default_allowed(
        self,
        element: ElementTree.Element,
        name: str,
        allowed: set[str],
        default: str,
        path: str,
    ) -> str:
        raw = element.get(gdocs_name(name))
        return (
            default if raw is None else parse_allowed(raw, allowed, f"{path}/@g:{name}")
        )

    def decode_default_integer(
        self, element: ElementTree.Element, name: str, default: int, path: str
    ) -> int:
        raw = element.get(gdocs_name(name))
        return default if raw is None else parse_integer(raw, f"{path}/@g:{name}")

    def decode_metadata_text_style(
        self, element: ElementTree.Element, path: str
    ) -> TextStyle | UnsetType:
        construct_text_style = parse_text_style(element, path)
        validate_whitespace(element, path)
        children = list(element)
        anchor = extract_one_child(children, xhtml_name("a"), path)
        link: Link | UnsetType = UNSET
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

    def decode_body(self, element: ElementTree.Element, path: str) -> Body:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        if not list(element):
            parse_error(path, "body must contain at least one section")
        content: list[StructuralElement] = []
        for index, section in enumerate(element):
            section_path = f"{path}/section[{index + 1}]"
            if section.tag != xhtml_name("section"):
                parse_error(path, "body content must be section elements")
            validate_attributes(section, set(), section_path)
            validate_whitespace(section, section_path)
            children = list(section)
            style = extract_one_child(
                children, gdocs_name("section-style"), section_path, required=True
            )
            assert style is not None
            style_path = f"{section_path}/g:section-style"
            content.append(
                SectionBreak(style=self.decode_section_style(style, style_path))
            )
            content.extend(
                self.decode_structural_sequence(
                    [child for child in children if child is not style],
                    section_path,
                    body=True,
                )
            )
        return Body(content=content)

    def decode_section_style(
        self, element: ElementTree.Element, path: str
    ) -> SectionStyle:
        scalar_names = {
            "column-separator-style",
            "content-direction",
            "section-type",
            "default-header-id",
            "default-footer-id",
            "even-page-header-id",
            "even-page-footer-id",
            "first-page-header-id",
            "first-page-footer-id",
            "use-first-page-header-footer",
            "flip-page-orientation",
            "page-number-start",
            "margin-top",
            "margin-bottom",
            "margin-left",
            "margin-right",
            "margin-header",
            "margin-footer",
        }
        validate_attributes(element, {gdocs_name(name) for name in scalar_names}, path)
        column_separator_style = self.optional_allowed(
            element,
            "column-separator-style",
            {"COLUMN_SEPARATOR_STYLE_UNSPECIFIED", "NONE", "BETWEEN_EACH_COLUMN"},
            path,
        )
        content_direction = self.optional_allowed(
            element, "content-direction", _DIRECTIONS, path
        )
        section_type = self.optional_allowed(
            element,
            "section-type",
            {"SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"},
            path,
        )
        default_header_id = optional_string(element, gdocs_name("default-header-id"))
        default_footer_id = optional_string(element, gdocs_name("default-footer-id"))
        even_page_header_id = optional_string(
            element, gdocs_name("even-page-header-id")
        )
        even_page_footer_id = optional_string(
            element, gdocs_name("even-page-footer-id")
        )
        first_page_header_id = optional_string(
            element, gdocs_name("first-page-header-id")
        )
        first_page_footer_id = optional_string(
            element, gdocs_name("first-page-footer-id")
        )
        use_first_page_header_footer = self.optional_boolean(
            element, "use-first-page-header-footer", path
        )
        flip_page_orientation = self.optional_boolean(
            element, "flip-page-orientation", path
        )
        page_number_start = self.optional_integer(element, "page-number-start", path)
        margin_top = self.optional_point(element, "margin-top", path)
        margin_bottom = self.optional_point(element, "margin-bottom", path)
        margin_left = self.optional_point(element, "margin-left", path)
        margin_right = self.optional_point(element, "margin-right", path)
        margin_header = self.optional_point(element, "margin-header", path)
        margin_footer = self.optional_point(element, "margin-footer", path)

        validate_whitespace(element, path)
        children = list(element)
        columns_element = extract_one_child(children, gdocs_name("columns"), path)
        columns: list[SectionColumn] | UnsetType = UNSET
        if columns_element is not None:
            columns = []
            columns_path = f"{path}/g:columns"
            validate_attributes(columns_element, set(), columns_path)
            validate_whitespace(columns_element, columns_path)
            for index, child in enumerate(columns_element):
                child_path = f"{columns_path}/g:column[{index + 1}]"
                if child.tag != gdocs_name("column"):
                    parse_error(
                        columns_path, f"unknown child element {display_name(child.tag)}"
                    )
                validate_attributes(
                    child, {gdocs_name("width"), gdocs_name("padding-end")}, child_path
                )
                width = self.required_point(child, "width", child_path)
                padding_end = self.required_point(child, "padding-end", child_path)
                validate_whitespace(child, child_path)
                _validate_no_children(child, child_path)
                columns.append(SectionColumn(width=width, padding_end=padding_end))
        for child in children:
            if child is not columns_element:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return SectionStyle(
            columns=columns,
            column_separator_style=column_separator_style,  # type: ignore[arg-type]
            content_direction=content_direction,  # type: ignore[arg-type]
            section_type=section_type,  # type: ignore[arg-type]
            default_header_id=default_header_id,
            default_footer_id=default_footer_id,
            even_page_header_id=even_page_header_id,
            even_page_footer_id=even_page_footer_id,
            first_page_header_id=first_page_header_id,
            first_page_footer_id=first_page_footer_id,
            use_first_page_header_footer=use_first_page_header_footer,
            flip_page_orientation=flip_page_orientation,
            page_number_start=page_number_start,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            margin_left=margin_left,
            margin_right=margin_right,
            margin_header=margin_header,
            margin_footer=margin_footer,
        )

    def optional_allowed(
        self, element: ElementTree.Element, name: str, allowed: set[str], path: str
    ) -> str | UnsetType:
        value = element.get(gdocs_name(name))
        return (
            UNSET
            if value is None
            else parse_allowed(value, allowed, f"{path}/@g:{name}")
        )

    def optional_boolean(
        self, element: ElementTree.Element, name: str, path: str
    ) -> bool | UnsetType:
        value = element.get(gdocs_name(name))
        return UNSET if value is None else parse_boolean(value, f"{path}/@g:{name}")

    def optional_integer(
        self, element: ElementTree.Element, name: str, path: str
    ) -> int | UnsetType:
        value = element.get(gdocs_name(name))
        return UNSET if value is None else parse_integer(value, f"{path}/@g:{name}")

    def optional_point(
        self, element: ElementTree.Element, name: str, path: str
    ) -> Dimension | UnsetType:
        value = element.get(gdocs_name(name))
        if value is None:
            return UNSET
        return Dimension(magnitude=parse_float(value, f"{path}/@g:{name}"), unit="PT")

    def required_point(
        self, element: ElementTree.Element, name: str, path: str
    ) -> Dimension:
        value = required_string(element, gdocs_name(name), path)
        return Dimension(magnitude=parse_float(value, f"{path}/@g:{name}"), unit="PT")

    def decode_segments(
        self, wrapper: ElementTree.Element, item_name: str, path: str
    ) -> dict[str, Segment]:
        validate_attributes(wrapper, set(), path)
        validate_whitespace(wrapper, path)
        result: dict[str, Segment] = {}
        for index, item in enumerate(wrapper):
            item_path = f"{path}/g:{item_name}[{index + 1}]"
            if item.tag != gdocs_name(item_name):
                parse_error(path, f"unknown child element {display_name(item.tag)}")
            validate_attributes(
                item, {gdocs_name("key"), gdocs_name("segment-id")}, item_path
            )
            key = required_string(item, gdocs_name("key"), item_path)
            segment_id = required_string(item, gdocs_name("segment-id"), item_path)
            validate_whitespace(item, item_path)
            if key in result:
                parse_error(item_path, f"duplicate segment key {key!r}")
            result[key] = Segment(
                segment_id=segment_id,
                content=self.decode_structural_sequence(list(item), item_path),
            )
        return result

    def decode_structural_sequence(
        self,
        elements: list[ElementTree.Element],
        path: str,
        body: bool = False,
    ) -> list[StructuralElement]:
        decoded: list[StructuralElement] = []
        for index, element in enumerate(elements):
            child_path = f"{path}/*[{index + 1}]"
            if element.tag == xhtml_name("section"):
                parse_error(child_path, "section elements are only valid in a body")
            if element.tag in _PARAGRAPH_TAGS:
                decoded.append(self.decode_paragraph(element, child_path))
            elif element.tag == gdocs_name("list"):
                decoded.extend(self.decode_list(element, child_path))
            elif element.tag == xhtml_name("table"):
                decoded.append(self.decode_table(element, child_path))
            elif element.tag == gdocs_name("table-of-contents"):
                validate_attributes(element, set(), child_path)
                validate_whitespace(element, child_path)
                decoded.append(
                    TableOfContents(
                        content=self.decode_structural_sequence(
                            list(element), child_path, body=False
                        )
                    )
                )
            else:
                parse_error(
                    child_path,
                    f"unknown structural element {display_name(element.tag)}",
                )
        return decoded

    def decode_list(self, element: ElementTree.Element, path: str) -> list[Paragraph]:
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
        result: list[Paragraph] = []
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
                UNSET
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
                Bullet(
                    list_id=cast(str, list_id), nesting_level=level, text_style=style
                )
                if preset is None
                else BulletPreset(preset=preset, nesting_level=level)  # type: ignore[arg-type]
            )
            result.append(paragraph)
        return result

    def decode_bullet_style(
        self, element: ElementTree.Element, path: str
    ) -> TextStyle | UnsetType:
        validate_attributes(element, text_style_attributes(), path)
        return self.decode_metadata_text_style(element, path)

    def decode_table(self, element: ElementTree.Element, path: str) -> Table:
        validate_attributes(element, {gdocs_name("table-key")}, path)
        table_key = element.get(gdocs_name("table-key"))
        validate_whitespace(element, path)
        children = list(element)
        colgroup = extract_one_child(children, xhtml_name("colgroup"), path)
        columns: list[TableColumn] | UnsetType = UNSET
        if colgroup is not None:
            columns = self.decode_table_columns(colgroup, f"{path}/colgroup")
        tbody = extract_one_child(children, xhtml_name("tbody"), path, required=True)
        assert tbody is not None
        tbody_path = f"{path}/tbody"
        validate_attributes(tbody, set(), tbody_path)
        validate_whitespace(tbody, tbody_path)
        rows: list[TableRow] = []
        for index, child in enumerate(tbody):
            if child.tag != xhtml_name("tr"):
                parse_error(
                    tbody_path, f"unknown child element {display_name(child.tag)}"
                )
            rows.append(self.decode_table_row(child, f"{tbody_path}/tr[{index + 1}]"))
        for child in children:
            if child not in (colgroup, tbody):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return Table(
            rows=rows,
            column_styles=columns,
            table_key=table_key,
        )

    def decode_table_columns(
        self, element: ElementTree.Element, path: str
    ) -> list[TableColumn]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: list[TableColumn] = []
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
                UNSET
                if raw_width is None
                else Dimension(
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
                    lambda: TableColumn(width_type=width_type, width=width),  # type: ignore[arg-type]
                )
            )
        return result

    def decode_table_row(self, element: ElementTree.Element, path: str) -> TableRow:
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
        cells: list[TableCell] = []
        for index, child in enumerate(element):
            if child.tag != xhtml_name("td"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            cells.append(self.decode_table_cell(child, f"{path}/td[{index + 1}]"))
        return TableRow(
            cells=cells,
            min_height=min_height,
            prevent_overflow=prevent_overflow,
            is_header=is_header,
            row_key=row_key,
        )

    def decode_table_cell(self, element: ElementTree.Element, path: str) -> TableCell:
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
            [child for child in children if child is not metadata], path
        )
        self.validate_cell_span(element, row_span, "rowspan", path)
        self.validate_cell_span(element, column_span, "colspan", path)
        style: TableCellStyle | UnsetType = UNSET
        if row_span != 1 or column_span != 1 or style_fields.has_values():
            style = construct_model(
                path,
                lambda: TableCellStyle(
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
        return TableCell(content=content, style=style, cell_key=cell_key)

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
            "Literal['CONTENT_ALIGNMENT_UNSPECIFIED', 'CONTENT_ALIGNMENT_UNSUPPORTED', 'TOP', 'MIDDLE', 'BOTTOM'] | UnsetType",
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
            UNSET
            if background is None
            else self.decode_optional_color(background, f"{path}/g:background-color")
        )
        border_left_element = extract_one_child(
            children, gdocs_name("border-left"), path
        )
        border_left = (
            UNSET
            if border_left_element is None
            else self.decode_table_cell_border(
                border_left_element, f"{path}/g:border-left"
            )
        )
        border_right_element = extract_one_child(
            children, gdocs_name("border-right"), path
        )
        border_right = (
            UNSET
            if border_right_element is None
            else self.decode_table_cell_border(
                border_right_element, f"{path}/g:border-right"
            )
        )
        border_top_element = extract_one_child(children, gdocs_name("border-top"), path)
        border_top = (
            UNSET
            if border_top_element is None
            else self.decode_table_cell_border(
                border_top_element, f"{path}/g:border-top"
            )
        )
        border_bottom_element = extract_one_child(
            children, gdocs_name("border-bottom"), path
        )
        border_bottom = (
            UNSET
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
    ) -> TableCellBorder:
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
        return TableCellBorder(
            color=decoded_color,
            width=width,
            dash_style=dash_style,  # type: ignore[arg-type]
        )

    def decode_paragraph(self, element: ElementTree.Element, path: str) -> Paragraph:
        children = list(element)
        declarative_tags = {SpanTag.tag_name, ParagraphStyleTag.tag_name}
        if element.tag == ParagraphTag.tag_name and all(
            child.tag in declarative_tags for child in children
        ):
            paragraph_tag = self.decode_tag(element, ParagraphTag, path)
            paragraph_children = cast(list[Node], paragraph_tag.children)
            style_tag = next(
                (
                    child
                    for child in paragraph_children
                    if isinstance(child, ParagraphStyleTag)
                ),
                None,
            )
            style = (
                ParagraphStyle(named_style_type="NORMAL_TEXT")
                if style_tag is None
                else self._decode_paragraph_style_tag(
                    style_tag,
                    f"{path}/g:paragraph-style",
                    owning_named_style="NORMAL_TEXT",
                )
            )
            elements: list[ParagraphElement] = []
            for index, child in enumerate(paragraph_children):
                if isinstance(child, SpanTag):
                    elements.append(
                        self._decode_text_run_span(
                            child, UNSET, f"{path}/*[{index + 1}]"
                        )
                    )
            return Paragraph(elements=elements, style=style)

        validate_attributes(element, set(), path)
        if element.text is not None and element.text.strip():
            parse_error(path, "unexpected text content")
        metadata = extract_one_child(children, gdocs_name("paragraph-style"), path)
        named_style_type = _PARAGRAPH_TAGS[element.tag]
        decoded_style: ParagraphStyle | UnsetType = UNSET
        if metadata is not None:
            metadata_path = f"{path}/g:paragraph-style"
            if metadata.get(gdocs_name("named-style-type")) is not None:
                parse_error(
                    metadata_path,
                    "named style type is owned by the paragraph element",
                )
            decoded_style = self._decode_paragraph_style_tag(
                self.decode_tag(metadata, ParagraphStyleTag, metadata_path),
                metadata_path,
                owning_named_style=named_style_type,
            )
        elif named_style_type is not UNSET:
            decoded_style = ParagraphStyle(named_style_type=named_style_type)  # type: ignore[arg-type]
        positioned = extract_one_child(children, gdocs_name("positioned-objects"), path)
        positioned_ids: list[str] | UnsetType = UNSET
        if positioned is not None:
            positioned_ids = self.decode_positioned_objects(
                positioned, f"{path}/g:positioned-objects"
            )
        runs: list[ParagraphElement] = []
        for index, child in enumerate(children):
            if child.tail is not None and child.tail.strip():
                parse_error(path, "unexpected text between paragraph elements")
            if child in (metadata, positioned):
                continue
            child_path = f"{path}/*[{index + 1}]"
            runs.append(self.decode_paragraph_element(child, child_path))
        return Paragraph(
            elements=runs,
            style=decoded_style,
            positioned_object_ids=positioned_ids,
        )

    def decode_paragraph_element(
        self, element: ElementTree.Element, path: str
    ) -> ParagraphElement:
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
        return self.decode_unlinked_paragraph_element(element, UNSET, path)

    def decode_unlinked_paragraph_element(
        self,
        element: ElementTree.Element,
        link: Link | UnsetType,
        path: str,
    ) -> ParagraphElement:
        if element.tag == xhtml_name("span"):
            return self.decode_text_run(element, link, path)
        if element.tag == gdocs_name("equation"):
            validate_attributes(element, set(), path)
            validate_whitespace(element, path)
            _validate_no_children(element, path)
            if link is not UNSET:
                parse_error(path, "equation cannot be a link target")
            return Equation()

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

        def finish_text_style() -> TextStyle | UnsetType:
            validate_whitespace(element, path)
            _validate_no_children(element, path)
            return construct_text_style(link)

        if element.tag == gdocs_name("auto-text"):
            auto_text_type = parse_allowed(
                required_string(element, gdocs_name("type"), path),
                {"TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"},
                f"{path}/@g:type",
            )
            return AutoText(
                auto_text_type=auto_text_type,  # type: ignore[arg-type]
                text_style=finish_text_style(),
            )
        if element.tag == gdocs_name("column-break"):
            return ColumnBreak(text_style=finish_text_style())
        if element.tag == xhtml_name("time"):
            date_id = required_string(element, gdocs_name("date-id"), path)
            raw_date_format = element.get(gdocs_name("date-format"))
            date_format = (
                UNSET
                if raw_date_format is None
                else parse_allowed(
                    raw_date_format, _DATE_FORMATS, f"{path}/@g:date-format"
                )
            )
            display_text = optional_string(element, gdocs_name("display-text"))
            locale = optional_string(element, gdocs_name("locale"))
            raw_time_format = element.get(gdocs_name("time-format"))
            time_format = (
                UNSET
                if raw_time_format is None
                else parse_allowed(
                    raw_time_format, _TIME_FORMATS, f"{path}/@g:time-format"
                )
            )
            time_zone_id = optional_string(element, gdocs_name("time-zone-id"))
            timestamp = optional_string(element, "datetime")
            return DateElement(
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
            return FootnoteReference(
                footnote_id=footnote_id,
                footnote_number=footnote_number,
                text_style=finish_text_style(),
            )
        if element.tag == xhtml_name("hr"):
            return HorizontalRule(text_style=finish_text_style())
        if element.tag == gdocs_name("inline-object"):
            inline_object_id = required_string(
                element, gdocs_name("inline-object-id"), path
            )
            return InlineObjectReference(
                inline_object_id=inline_object_id,
                text_style=finish_text_style(),
            )
        if element.tag == gdocs_name("page-break"):
            return PageBreak(text_style=finish_text_style())
        if element.tag == gdocs_name("person"):
            person_id = required_string(element, gdocs_name("person-id"), path)
            email = optional_string(element, gdocs_name("email"))
            name = optional_string(element, gdocs_name("name"))
            return PersonReference(
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
        return RichLink(
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
        style_tag: ParagraphStyleTag,
        path: str,
        *,
        owning_named_style: object = UNSET,
    ) -> ParagraphStyle:
        values = {
            name: getattr(style_tag, name)
            for name in type(style_tag).fields()
            if name != "children"
        }
        if not isinstance(style_tag, NamedParagraphStyleTag):
            values["named_style_type"] = owning_named_style
        border_fields: dict[type[Node], str] = {
            BorderBetweenTag: "border_between",
            BorderTopTag: "border_top",
            BorderBottomTag: "border_bottom",
            BorderLeftTag: "border_left",
            BorderRightTag: "border_right",
        }
        children = cast(list[Node], style_tag.children)
        for child in children:
            field_name = border_fields.get(type(child))
            if field_name is not None:
                assert isinstance(child, ParagraphBorderTag)
                values[field_name] = self._decode_paragraph_border_tag(
                    child, f"{path}/{display_name(child.tag_name or '')}"
                )
            elif isinstance(child, ShadingColorTag):
                values["shading_color"] = cast(Color | None, child.color)
            elif isinstance(child, TabStopsTag):
                values["tab_stops"] = [
                    TabStop(
                        alignment=cast(Any, stop.alignment),
                        offset=cast(Dimension, stop.offset),
                    )
                    for stop in cast(list[TabStopTag], child.children)
                ]

        return construct_model(
            path,
            lambda: ParagraphStyle(**cast(Any, values)),
        )

    def _decode_paragraph_border_tag(
        self, border_tag: ParagraphBorderTag, path: str
    ) -> ParagraphBorder:
        children = cast(list[Node], border_tag.children)
        color_tag = cast(ColorTag, children[0])
        return construct_model(
            path,
            lambda: ParagraphBorder(
                color=cast(Color | None, color_tag.color),
                width=cast(Dimension, border_tag.width),
                padding=cast(Dimension, border_tag.padding),
                dash_style=cast(Any, border_tag.dash_style),
            ),
        )

    def decode_optional_color(
        self, element: ElementTree.Element, path: str
    ) -> Color | None:
        names = {
            name: gdocs_name(name) for name in ("red", "green", "blue", "transparent")
        }
        validate_attributes(element, set(names.values()), path)
        transparent = element.get(names["transparent"])
        transparent_value = (
            UNSET
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
            return Color(red=red, green=green, blue=blue)
        except ValueError as error:
            parse_error(path, str(error), cause=error)

    def decode_linked_text_run(self, anchor: ElementTree.Element, path: str) -> TextRun:
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
        self, span: ElementTree.Element, link: Link | UnsetType, path: str
    ) -> TextRun:
        return self._decode_text_run_span(
            self.decode_tag(span, SpanTag, path), link, path
        )

    def _decode_text_run_span(
        self, span_tag: SpanTag, link: Link | UnsetType, path: str
    ) -> TextRun:
        style_values = {
            name: getattr(span_tag, name)
            for name in SpanTag.fields()
            if name != "children"
        }
        text_style: TextStyle | UnsetType = UNSET
        if (
            any(value is not UNSET for value in style_values.values())
            or link is not UNSET
        ):
            text_style = construct_model(
                path,
                lambda: TextStyle(**cast(Any, style_values), link=link),
            )

        content = ""
        children = cast(list[Node], span_tag.children)
        for child in children:
            if isinstance(child, Text):
                content += child.value
            else:
                assert isinstance(child, BreakTag)
                content += "\n"
        return TextRun(content=content, text_style=text_style)


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


def deserialize_document(xhtml: str) -> Document:
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
        return _Decoder().decode_document(root)
    except XHTMLParseError:
        raise
    except (ElementTree.ParseError, RecursionError) as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error
