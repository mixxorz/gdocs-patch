from typing import cast
from xml.etree import ElementTree

from gdocs_patch.models import UNSET, Document, DocumentTab, StructuralElement, Tab

from .base import (
    GDOCS_NAMESPACE,
    XHTML_NAMESPACE,
    XML_DECLARATION,
    _indent_xml,  # pyright: ignore[reportPrivateUsage]
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
        if tab.content is not UNSET:
            raise ValueError("Tab.content is not supported yet")

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

        if tab.children:
            child_tabs = ElementTree.SubElement(element, gdocs_name("child-tabs"))
            for child in tab.children:
                child_tabs.append(self.encode_tab(child))
        return element

    def encode_document_tab(self, document_tab: DocumentTab) -> ElementTree.Element:
        raise ValueError("DocumentTab content is not supported yet")

    def encode_structural_sequence(
        self, elements: list[StructuralElement]
    ) -> list[ElementTree.Element]:
        raise ValueError("Structural content is not supported yet")


def serialize_document(document: Document) -> str:
    ElementTree.register_namespace("", XHTML_NAMESPACE)
    ElementTree.register_namespace("g", GDOCS_NAMESPACE)
    root = _Encoder().encode_document(document)
    _indent_xml(root)
    xml = ElementTree.tostring(root, encoding="unicode", short_empty_elements=True)
    return f"{XML_DECLARATION}\n{xml}\n"
