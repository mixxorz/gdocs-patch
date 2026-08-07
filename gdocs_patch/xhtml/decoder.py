from typing import Literal, cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    Body,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Link,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
    SectionBreak,
    SectionColumn,
    SectionStyle,
    Segment,
    StructuralElement,
    Tab,
    TabStop,
    TextRun,
    UnsetType,
)

from .base import (
    XML_DECLARATION,
    XHTMLParseError,
    decode_link,
    decode_text_style,
    display_name,
    extract_one_child,
    gdocs_name,
    optional_string,
    parse_allowed,
    parse_boolean,
    parse_error,
    parse_float,
    parse_integer,
    required_string,
    text_style_attributes,
    validate_attributes,
    validate_whitespace,
    xhtml_name,
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
_ALIGNMENTS = {"ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END", "JUSTIFIED"}
_DIRECTIONS = {"CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"}
_SPACING_MODES = {"SPACING_MODE_UNSPECIFIED", "NEVER_COLLAPSE", "COLLAPSE_LISTS"}
_DASH_STYLES = {"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"}
_TAB_ALIGNMENTS = {"TAB_STOP_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"}

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


SuggestionsViewMode = Literal[
    "DEFAULT_FOR_CURRENT_ACCESS",
    "SUGGESTIONS_INLINE",
    "PREVIEW_SUGGESTIONS_ACCEPTED",
    "PREVIEW_WITHOUT_SUGGESTIONS",
]


class _Decoder:
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
        validate_whitespace(root, path)
        children = list(root)
        body = extract_one_child(children, xhtml_name("body"), path, required=True)
        assert body is not None
        for child in children:
            if child is not body:
                parse_error(path, f"unknown child element {display_name(child.tag)}")

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
        return Document(
            document_id=required_string(root, gdocs_name("document-id"), path),
            title=required_string(root, gdocs_name("title"), path),
            revision_id=optional_string(root, gdocs_name("revision-id")),
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
        validate_whitespace(element, path)
        children = list(element)
        document_tab = extract_one_child(children, gdocs_name("document-tab"), path)
        child_tabs = extract_one_child(children, gdocs_name("child-tabs"), path)
        for child in children:
            if child not in (document_tab, child_tabs):
                parse_error(path, f"unknown child element {display_name(child.tag)}")

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
        raw_level = element.get(gdocs_name("nesting-level"))
        return Tab(
            tab_id=required_string(element, gdocs_name("tab-id"), path),
            title=required_string(element, gdocs_name("title"), path),
            index=parse_integer(
                required_string(element, gdocs_name("index"), path),
                f"{path}/@g:index",
            ),
            nesting_level=(
                0
                if raw_level is None
                else parse_integer(raw_level, f"{path}/@g:nesting-level")
            ),
            parent_tab_id=optional_string(element, gdocs_name("parent-tab-id")),
            icon_emoji=optional_string(element, gdocs_name("icon-emoji")),
            content=(
                UNSET
                if document_tab is None
                else self.decode_document_tab(document_tab, f"{path}/g:document-tab")
            ),
            children=decoded_children,
        )

    def decode_document_tab(
        self, element: ElementTree.Element, path: str
    ) -> DocumentTab:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        children = list(element)
        supported = {
            gdocs_name("body"),
            gdocs_name("headers"),
            gdocs_name("footers"),
            gdocs_name("footnotes"),
        }
        for child in children:
            if child.tag not in supported:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        body = extract_one_child(children, gdocs_name("body"), path)
        headers = extract_one_child(children, gdocs_name("headers"), path)
        footers = extract_one_child(children, gdocs_name("footers"), path)
        footnotes = extract_one_child(children, gdocs_name("footnotes"), path)
        return DocumentTab(
            body=UNSET if body is None else self.decode_body(body, f"{path}/g:body"),
            headers=(
                UNSET
                if headers is None
                else self.decode_segments(headers, "header", f"{path}/g:headers")
            ),
            footers=(
                UNSET
                if footers is None
                else self.decode_segments(footers, "footer", f"{path}/g:footers")
            ),
            footnotes=(
                UNSET
                if footnotes is None
                else self.decode_segments(footnotes, "footnote", f"{path}/g:footnotes")
            ),
        )

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
        validate_whitespace(element, path)
        children = list(element)
        columns_element = extract_one_child(children, gdocs_name("columns"), path)
        for child in children:
            if child is not columns_element:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
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
                validate_whitespace(child, child_path)
                _validate_no_children(child, child_path)
                columns.append(
                    SectionColumn(
                        width=self.required_point(child, "width", child_path),
                        padding_end=self.required_point(
                            child, "padding-end", child_path
                        ),
                    )
                )
        return SectionStyle(
            columns=columns,
            column_separator_style=self.optional_allowed(
                element,
                "column-separator-style",
                {"COLUMN_SEPARATOR_STYLE_UNSPECIFIED", "NONE", "BETWEEN_EACH_COLUMN"},
                path,
            ),  # type: ignore[arg-type]
            content_direction=self.optional_allowed(
                element, "content-direction", _DIRECTIONS, path
            ),  # type: ignore[arg-type]
            section_type=self.optional_allowed(
                element,
                "section-type",
                {"SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"},
                path,
            ),  # type: ignore[arg-type]
            default_header_id=optional_string(element, gdocs_name("default-header-id")),
            default_footer_id=optional_string(element, gdocs_name("default-footer-id")),
            even_page_header_id=optional_string(
                element, gdocs_name("even-page-header-id")
            ),
            even_page_footer_id=optional_string(
                element, gdocs_name("even-page-footer-id")
            ),
            first_page_header_id=optional_string(
                element, gdocs_name("first-page-header-id")
            ),
            first_page_footer_id=optional_string(
                element, gdocs_name("first-page-footer-id")
            ),
            use_first_page_header_footer=self.optional_boolean(
                element, "use-first-page-header-footer", path
            ),
            flip_page_orientation=self.optional_boolean(
                element, "flip-page-orientation", path
            ),
            page_number_start=self.optional_integer(element, "page-number-start", path),
            margin_top=self.optional_point(element, "margin-top", path),
            margin_bottom=self.optional_point(element, "margin-bottom", path),
            margin_left=self.optional_point(element, "margin-left", path),
            margin_right=self.optional_point(element, "margin-right", path),
            margin_header=self.optional_point(element, "margin-header", path),
            margin_footer=self.optional_point(element, "margin-footer", path),
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
            validate_whitespace(item, item_path)
            key = required_string(item, gdocs_name("key"), item_path)
            if key in result:
                parse_error(item_path, f"duplicate segment key {key!r}")
            result[key] = Segment(
                segment_id=required_string(item, gdocs_name("segment-id"), item_path),
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
            else:
                parse_error(
                    child_path,
                    f"unknown structural element {display_name(element.tag)}",
                )
        return decoded

    def decode_paragraph(self, element: ElementTree.Element, path: str) -> Paragraph:
        validate_attributes(element, set(), path)
        if element.text is not None and element.text.strip():
            parse_error(path, "unexpected text content")
        children = list(element)
        metadata = extract_one_child(children, gdocs_name("paragraph-style"), path)
        positioned = extract_one_child(children, gdocs_name("positioned-objects"), path)
        named_style_type = _PARAGRAPH_TAGS[element.tag]
        decoded_style: ParagraphStyle | UnsetType = UNSET
        if metadata is not None:
            decoded_style = self.decode_paragraph_style(
                metadata,
                f"{path}/g:paragraph-style",
                owning_named_style=named_style_type,
                paragraph_owns_named_style=True,
            )
        elif named_style_type is not UNSET:
            decoded_style = ParagraphStyle(named_style_type=named_style_type)  # type: ignore[arg-type]
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
            if child.tag == xhtml_name("span"):
                runs.append(self.decode_text_run(child, UNSET, child_path))
            elif child.tag == xhtml_name("a"):
                runs.append(self.decode_linked_text_run(child, child_path))
            else:
                parse_error(
                    child_path, f"unknown paragraph element {display_name(child.tag)}"
                )
        return Paragraph(
            elements=runs,
            style=decoded_style,
            positioned_object_ids=positioned_ids,
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
            validate_whitespace(child, child_path)
            _validate_no_children(child, child_path)
            result.append(required_string(child, gdocs_name("id"), child_path))
        return result

    def decode_paragraph_style(
        self,
        element: ElementTree.Element,
        path: str,
        *,
        owning_named_style: str | UnsetType = UNSET,
        paragraph_owns_named_style: bool = False,
    ) -> ParagraphStyle:
        attribute_names = {
            "named-style-type",
            "alignment",
            "direction",
            "line-spacing",
            "spacing-mode",
            "space-above",
            "space-below",
            "indent-first-line",
            "indent-start",
            "indent-end",
            "keep-lines-together",
            "keep-with-next",
            "avoid-widow-and-orphan",
            "page-break-before",
            "heading-id",
        }
        validate_attributes(
            element, {gdocs_name(name) for name in attribute_names}, path
        )
        validate_whitespace(element, path)
        raw_named_style = element.get(gdocs_name("named-style-type"))
        if paragraph_owns_named_style and raw_named_style is not None:
            parse_error(path, "named style type is owned by the paragraph element")
        named_style = owning_named_style
        if raw_named_style is not None:
            named_style = parse_allowed(
                raw_named_style, _NAMED_STYLE_TYPES, f"{path}/@g:named-style-type"
            )
        border_names = (
            "border-between",
            "border-top",
            "border-bottom",
            "border-left",
            "border-right",
        )
        children = list(element)
        borders: dict[str, ParagraphBorder | UnsetType] = {}
        for name in border_names:
            child = extract_one_child(children, gdocs_name(name), path)
            borders[name] = (
                UNSET
                if child is None
                else self.decode_paragraph_border(child, f"{path}/g:{name}")
            )
        shading = extract_one_child(children, gdocs_name("shading-color"), path)
        tab_stops_element = extract_one_child(children, gdocs_name("tab-stops"), path)
        known = {gdocs_name(name) for name in border_names} | {
            gdocs_name("shading-color"),
            gdocs_name("tab-stops"),
        }
        for child in children:
            if child.tag not in known:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        tab_stops: list[TabStop] | UnsetType = UNSET
        if tab_stops_element is not None:
            tab_stops = self.decode_tab_stops(tab_stops_element, f"{path}/g:tab-stops")
        line_spacing_raw = element.get(gdocs_name("line-spacing"))
        return ParagraphStyle(
            named_style_type=named_style,  # type: ignore[arg-type]
            alignment=self.optional_allowed(element, "alignment", _ALIGNMENTS, path),  # type: ignore[arg-type]
            direction=self.optional_allowed(element, "direction", _DIRECTIONS, path),  # type: ignore[arg-type]
            line_spacing=UNSET
            if line_spacing_raw is None
            else parse_float(line_spacing_raw, f"{path}/@g:line-spacing"),
            spacing_mode=self.optional_allowed(
                element, "spacing-mode", _SPACING_MODES, path
            ),  # type: ignore[arg-type]
            space_above=self.optional_point(element, "space-above", path),
            space_below=self.optional_point(element, "space-below", path),
            indent_first_line=self.optional_point(element, "indent-first-line", path),
            indent_start=self.optional_point(element, "indent-start", path),
            indent_end=self.optional_point(element, "indent-end", path),
            keep_lines_together=self.optional_boolean(
                element, "keep-lines-together", path
            ),
            keep_with_next=self.optional_boolean(element, "keep-with-next", path),
            avoid_widow_and_orphan=self.optional_boolean(
                element, "avoid-widow-and-orphan", path
            ),
            page_break_before=self.optional_boolean(element, "page-break-before", path),
            heading_id=optional_string(element, gdocs_name("heading-id")),
            border_between=borders["border-between"],
            border_top=borders["border-top"],
            border_bottom=borders["border-bottom"],
            border_left=borders["border-left"],
            border_right=borders["border-right"],
            shading_color=UNSET
            if shading is None
            else self.decode_optional_color(shading, f"{path}/g:shading-color"),
            tab_stops=tab_stops,
        )

    def decode_paragraph_border(
        self, element: ElementTree.Element, path: str
    ) -> ParagraphBorder:
        validate_attributes(
            element,
            {gdocs_name("dash-style"), gdocs_name("width"), gdocs_name("padding")},
            path,
        )
        validate_whitespace(element, path)
        children = list(element)
        color = extract_one_child(children, gdocs_name("color"), path, required=True)
        assert color is not None
        for child in children:
            if child is not color:
                parse_error(path, f"unknown child element {display_name(child.tag)}")
        return ParagraphBorder(
            color=self.decode_optional_color(color, f"{path}/g:color"),
            width=self.required_point(element, "width", path),
            padding=self.required_point(element, "padding", path),
            dash_style=parse_allowed(
                required_string(element, gdocs_name("dash-style"), path),
                _DASH_STYLES,
                f"{path}/@g:dash-style",
            ),  # type: ignore[arg-type]
        )

    def decode_optional_color(
        self, element: ElementTree.Element, path: str
    ) -> Color | None:
        names = {
            name: gdocs_name(name) for name in ("red", "green", "blue", "transparent")
        }
        validate_attributes(element, set(names.values()), path)
        validate_whitespace(element, path)
        _validate_no_children(element, path)
        transparent = element.get(names["transparent"])
        components = [element.get(names[name]) for name in ("red", "green", "blue")]
        if transparent is not None:
            if not parse_boolean(transparent, f"{path}/@g:transparent") or any(
                value is not None for value in components
            ):
                parse_error(path, "transparent color cannot include RGB components")
            return None
        if not all(value is not None for value in components):
            parse_error(path, "opaque color requires red, green, and blue")
        try:
            return Color(
                red=parse_float(cast(str, components[0]), f"{path}/@g:red"),
                green=parse_float(cast(str, components[1]), f"{path}/@g:green"),
                blue=parse_float(cast(str, components[2]), f"{path}/@g:blue"),
            )
        except ValueError as error:
            parse_error(path, str(error))

    def decode_tab_stops(
        self, element: ElementTree.Element, path: str
    ) -> list[TabStop]:
        validate_attributes(element, set(), path)
        validate_whitespace(element, path)
        result: list[TabStop] = []
        for index, child in enumerate(element):
            child_path = f"{path}/g:tab-stop[{index + 1}]"
            if child.tag != gdocs_name("tab-stop"):
                parse_error(path, f"unknown child element {display_name(child.tag)}")
            validate_attributes(
                child, {gdocs_name("alignment"), gdocs_name("offset")}, child_path
            )
            validate_whitespace(child, child_path)
            _validate_no_children(child, child_path)
            result.append(
                TabStop(
                    alignment=parse_allowed(
                        required_string(child, gdocs_name("alignment"), child_path),
                        _TAB_ALIGNMENTS,
                        f"{child_path}/@g:alignment",
                    ),  # type: ignore[arg-type]
                    offset=self.required_point(child, "offset", child_path),
                )
            )
        return result

    def decode_linked_text_run(self, anchor: ElementTree.Element, path: str) -> TextRun:
        if anchor.text is not None and anchor.text.strip():
            parse_error(path, "unexpected text in link")
        link = decode_link(anchor, path)
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
        validate_attributes(span, text_style_attributes(), path)
        content = span.text or ""
        for child in span:
            if child.tag != xhtml_name("br"):
                parse_error(path, f"unknown span child {display_name(child.tag)}")
            child_path = f"{path}/br"
            validate_attributes(child, set(), child_path)
            if child.text:
                parse_error(child_path, "br must be empty")
            _validate_no_children(child, child_path)
            content += "\n" + (child.tail or "")
        return TextRun(
            content=content,
            text_style=decode_text_style(span, link, path),
        )


def deserialize_document(xhtml: str) -> Document:
    if not xhtml.startswith(XML_DECLARATION):
        raise XHTMLParseError(
            "/document: required XML declaration is missing or invalid"
        )
    payload = xhtml[len(XML_DECLARATION) :].lstrip()
    try:
        root = ElementTree.fromstring(payload)
    except ElementTree.ParseError as error:
        raise XHTMLParseError(f"/document: malformed XML: {error}") from error
    return _Decoder().decode_document(root)
