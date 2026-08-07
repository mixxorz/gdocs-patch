from typing import Literal, cast
from xml.etree import ElementTree

from gdocs_patch.models import (
    UNSET,
    Document,
    DocumentTab,
    StructuralElement,
    Tab,
    UnsetType,
)

from .base import (
    XML_DECLARATION,
    XHTMLParseError,
    extract_one_child,
    gdocs_name,
    optional_string,
    parse_allowed,
    parse_error,
    parse_integer,
    required_string,
    validate_attributes,
    validate_whitespace,
    xhtml_name,
)

_SUGGESTIONS_VIEW_MODES = {
    "DEFAULT_FOR_CURRENT_ACCESS",
    "SUGGESTIONS_INLINE",
    "PREVIEW_SUGGESTIONS_ACCEPTED",
    "PREVIEW_WITHOUT_SUGGESTIONS",
}
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

        allowed_attributes = {
            gdocs_name("document-id"),
            gdocs_name("title"),
            gdocs_name("revision-id"),
            gdocs_name("suggestions-view-mode"),
        }
        validate_attributes(root, allowed_attributes, path)
        validate_whitespace(root, path)

        children = list(root)
        body = extract_one_child(children, xhtml_name("body"), path, required=True)
        assert body is not None
        for child in children:
            if child is not body:
                parse_error(path, f"unknown child element {child.tag}")

        document_id = required_string(root, gdocs_name("document-id"), path)
        title = required_string(root, gdocs_name("title"), path)
        revision_id = optional_string(root, gdocs_name("revision-id"))
        raw_mode = root.get(gdocs_name("suggestions-view-mode"))
        suggestions_view_mode: SuggestionsViewMode | UnsetType
        if raw_mode is None:
            suggestions_view_mode = UNSET
        else:
            suggestions_view_mode = cast(
                "SuggestionsViewMode",
                parse_allowed(
                    raw_mode,
                    _SUGGESTIONS_VIEW_MODES,
                    f"{path}/@g:suggestions-view-mode",
                ),
            )

        return Document(
            document_id=document_id,
            title=title,
            revision_id=revision_id,
            suggestions_view_mode=suggestions_view_mode,
            tabs=self.decode_tabs(body, f"{path}/body"),
        )

    def decode_tabs(self, body: ElementTree.Element, path: str) -> list[Tab]:
        validate_attributes(body, set(), path)
        validate_whitespace(body, path)
        tabs: list[Tab] = []
        for index, child in enumerate(body):
            if child.tag != gdocs_name("tab"):
                parse_error(path, f"unknown child element {child.tag}")
            tabs.append(self.decode_tab(child, f"{path}/g:tab[{index + 1}]"))
        return tabs

    def decode_tab(self, element: ElementTree.Element, path: str) -> Tab:
        allowed_attributes = {
            gdocs_name("tab-id"),
            gdocs_name("title"),
            gdocs_name("index"),
            gdocs_name("nesting-level"),
            gdocs_name("parent-tab-id"),
            gdocs_name("icon-emoji"),
        }
        validate_attributes(element, allowed_attributes, path)
        validate_whitespace(element, path)

        children = list(element)
        child_tabs = extract_one_child(children, gdocs_name("child-tabs"), path)
        for child in children:
            if child is not child_tabs:
                parse_error(path, f"unknown child element {child.tag}")

        decoded_children: list[Tab] = []
        if child_tabs is not None:
            child_path = f"{path}/g:child-tabs"
            validate_attributes(child_tabs, set(), child_path)
            validate_whitespace(child_tabs, child_path)
            for index, child in enumerate(child_tabs):
                if child.tag != gdocs_name("tab"):
                    parse_error(child_path, f"unknown child element {child.tag}")
                decoded_children.append(
                    self.decode_tab(child, f"{child_path}/g:tab[{index + 1}]")
                )

        raw_nesting_level = element.get(gdocs_name("nesting-level"))
        nesting_level = (
            0
            if raw_nesting_level is None
            else parse_integer(raw_nesting_level, f"{path}/@g:nesting-level")
        )
        return Tab(
            tab_id=required_string(element, gdocs_name("tab-id"), path),
            title=required_string(element, gdocs_name("title"), path),
            index=parse_integer(
                required_string(element, gdocs_name("index"), path),
                f"{path}/@g:index",
            ),
            nesting_level=nesting_level,
            parent_tab_id=optional_string(element, gdocs_name("parent-tab-id")),
            icon_emoji=optional_string(element, gdocs_name("icon-emoji")),
            children=decoded_children,
        )

    def decode_document_tab(
        self, element: ElementTree.Element, path: str
    ) -> DocumentTab:
        parse_error(path, "DocumentTab content is not supported yet")

    def decode_structural_sequence(
        self, elements: list[ElementTree.Element], path: str
    ) -> list[StructuralElement]:
        parse_error(path, "structural content is not supported yet")


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
