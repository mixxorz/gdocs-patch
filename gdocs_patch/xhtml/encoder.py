from typing import cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    Body,
    Document,
    DocumentTab,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Segment,
    StructuralElement,
    Tab,
    TextRun,
    UnsetType,
)

from .base import (
    GDOCS_NAMESPACE,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    _indent_xml,  # pyright: ignore[reportPrivateUsage]
    encode_text_style,
    gdocs_name,
    xhtml_name,
)


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
        if section_break.style != SectionStyle():
            raise ValueError("SectionStyle fields are not supported yet")
        ElementTree.SubElement(section, gdocs_name("section-style"))

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
        if paragraph.positioned_object_ids is not UNSET:
            raise ValueError("positioned objects are not supported yet")
        tag = gdocs_name("paragraph")
        if paragraph.style is not UNSET:
            style = cast(ParagraphStyle, paragraph.style)
            if style == ParagraphStyle(named_style_type="NORMAL_TEXT"):
                tag = xhtml_name("p")
            elif style != ParagraphStyle():
                raise ValueError("ParagraphStyle fields are not supported yet")
        element = ElementTree.Element(tag)
        for item in paragraph.elements:
            if not isinstance(item, TextRun):
                raise ValueError(f"unsupported paragraph element {type(item).__name__}")
            element.append(self.encode_text_run(item))
        return element

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
