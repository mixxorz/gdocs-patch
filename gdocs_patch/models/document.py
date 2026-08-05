from __future__ import annotations

from typing import Literal

from .base import UNSET, Color, Dimension, Model, UnsetType


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
