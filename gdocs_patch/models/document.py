from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from .base import UNSET, Color, Dimension, Model, UnsetType

if TYPE_CHECKING:
    from .list import ListDefinition
    from .paragraph import NamedStyle


class StructuralElement(Model):
    """Base for document structures whose absolute indices are derived."""


class TableOfContents(StructuralElement):
    def __init__(self, *, content: list[StructuralElement]) -> None:
        self.content = content


class DocumentStyle(Model):
    def __init__(
        self,
        *,
        background_color: Color | None | UnsetType = UNSET,
        document_mode: Literal[
            "DOCUMENT_MODE_UNSPECIFIED",
            "PAGES",
            "PAGELESS",
        ]
        | UnsetType = UNSET,
        page_width: Dimension | UnsetType = UNSET,
        page_height: Dimension | UnsetType = UNSET,
        margin_top: Dimension | UnsetType = UNSET,
        margin_bottom: Dimension | UnsetType = UNSET,
        margin_left: Dimension | UnsetType = UNSET,
        margin_right: Dimension | UnsetType = UNSET,
        margin_header: Dimension | UnsetType = UNSET,
        margin_footer: Dimension | UnsetType = UNSET,
        default_header_id: str | UnsetType = UNSET,
        default_footer_id: str | UnsetType = UNSET,
        even_page_header_id: str | UnsetType = UNSET,
        even_page_footer_id: str | UnsetType = UNSET,
        first_page_header_id: str | UnsetType = UNSET,
        first_page_footer_id: str | UnsetType = UNSET,
        use_even_page_header_footer: bool | UnsetType = UNSET,
        use_first_page_header_footer: bool | UnsetType = UNSET,
        use_custom_header_footer_margins: bool | UnsetType = UNSET,
        flip_page_orientation: bool | UnsetType = UNSET,
        page_number_start: int | UnsetType = UNSET,
    ) -> None:
        self.background_color = background_color
        self.document_mode = document_mode
        self.page_width = page_width
        self.page_height = page_height
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_header = margin_header
        self.margin_footer = margin_footer
        self.default_header_id = default_header_id
        self.default_footer_id = default_footer_id
        self.even_page_header_id = even_page_header_id
        self.even_page_footer_id = even_page_footer_id
        self.first_page_header_id = first_page_header_id
        self.first_page_footer_id = first_page_footer_id
        self.use_even_page_header_footer = use_even_page_header_footer
        self.use_first_page_header_footer = use_first_page_header_footer
        self.use_custom_header_footer_margins = use_custom_header_footer_margins
        self.flip_page_orientation = flip_page_orientation
        self.page_number_start = page_number_start


class Segment(Model):
    def __init__(
        self,
        *,
        segment_id: str,
        content: list[StructuralElement],
    ) -> None:
        self.segment_id = segment_id
        self.content = content


class DocumentTab(Model):
    def __init__(
        self,
        *,
        body: list[StructuralElement] | UnsetType = UNSET,
        headers: dict[str, Segment] | UnsetType = UNSET,
        footers: dict[str, Segment] | UnsetType = UNSET,
        footnotes: dict[str, Segment] | UnsetType = UNSET,
        document_style: DocumentStyle | UnsetType = UNSET,
        named_styles: list[NamedStyle] | UnsetType = UNSET,
        lists: dict[str, ListDefinition] | UnsetType = UNSET,
    ) -> None:
        self.body = body
        self.headers = headers
        self.footers = footers
        self.footnotes = footnotes
        self.document_style = document_style
        self.named_styles = named_styles
        self.lists = lists


class Tab(Model):
    def __init__(
        self,
        *,
        tab_id: str,
        title: str,
        index: int,
        children: list[Tab],
        nesting_level: int = 0,
        parent_tab_id: str | UnsetType = UNSET,
        icon_emoji: str | UnsetType = UNSET,
        content: DocumentTab | UnsetType = UNSET,
    ) -> None:
        self.tab_id = tab_id
        self.title = title
        self.index = index
        self.nesting_level = nesting_level
        self.parent_tab_id = parent_tab_id
        self.icon_emoji = icon_emoji
        self.content = content
        self.children = children


class Document(Model):
    def __init__(
        self,
        *,
        document_id: str,
        title: str,
        tabs: list[Tab],
        revision_id: str | UnsetType = UNSET,
        suggestions_view_mode: Literal[
            "DEFAULT_FOR_CURRENT_ACCESS",
            "SUGGESTIONS_INLINE",
            "PREVIEW_SUGGESTIONS_ACCEPTED",
            "PREVIEW_WITHOUT_SUGGESTIONS",
        ]
        | UnsetType = UNSET,
        legacy_tab: DocumentTab | UnsetType = UNSET,
    ) -> None:
        self.document_id = document_id
        self.title = title
        self.revision_id = revision_id
        self.suggestions_view_mode = suggestions_view_mode
        self.tabs = tabs
        self.legacy_tab = legacy_tab
