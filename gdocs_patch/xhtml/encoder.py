from typing import cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    Body,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Paragraph,
    ParagraphBorder,
    ParagraphStyle,
    SectionBreak,
    SectionColumn,
    Segment,
    StructuralElement,
    Tab,
    TabStop,
    TextRun,
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
        if document_tab.document_style is not UNSET:
            raise ValueError("DocumentStyle is not supported yet")
        if document_tab.named_styles is not UNSET:
            raise ValueError("named styles are not supported yet")
        if document_tab.lists is not UNSET:
            raise ValueError("list definitions are not supported yet")
        element = ElementTree.Element(gdocs_name("document-tab"))
        if document_tab.body is not UNSET:
            element.append(self.encode_body(cast(Body, document_tab.body)))
        self.encode_segments(element, "headers", "header", document_tab.headers)
        self.encode_segments(element, "footers", "footer", document_tab.footers)
        self.encode_segments(element, "footnotes", "footnote", document_tab.footnotes)
        return element

    def encode_body(self, body: Body) -> ElementTree.Element:
        element = ElementTree.Element(gdocs_name("body"))
        if not body.content or not isinstance(body.content[0], SectionBreak):
            raise ValueError("Body.content must begin with SectionBreak")
        current: ElementTree.Element | None = None
        for node in body.content:
            if isinstance(node, SectionBreak):
                current = ElementTree.SubElement(element, xhtml_name("section"))
                self.encode_section_style(current, node)
            else:
                assert current is not None
                current.extend(self.encode_structural_sequence([node], body=True))
        return element

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
        for element in elements:
            if isinstance(element, SectionBreak):
                if body:
                    raise ValueError("SectionBreak must be projected as a section")
                raise ValueError("SectionBreak is only valid in a body")
            if isinstance(element, Paragraph):
                encoded.append(self.encode_paragraph(element))
            else:
                raise ValueError(
                    f"unsupported structural element {type(element).__name__}"
                )
        return encoded

    def encode_paragraph(self, paragraph: Paragraph) -> ElementTree.Element:
        if paragraph.bullet is not UNSET:
            raise ValueError("paragraph bullets are not supported yet")
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
            if not isinstance(item, TextRun):
                raise ValueError(f"unsupported paragraph element {type(item).__name__}")
            element.append(self.encode_text_run(item))
        return element

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
