from typing import Literal

from .base import UNSET, Dimension, Model, UnsetType
from .document import StructuralElement


class SectionColumn(Model):
    def __init__(
        self,
        *,
        width: Dimension,
        padding_end: Dimension,
    ) -> None:
        self.width = width
        self.padding_end = padding_end


class SectionStyle(Model):
    def __init__(
        self,
        *,
        columns: list[SectionColumn] | UnsetType = UNSET,
        column_separator_style: Literal[
            "COLUMN_SEPARATOR_STYLE_UNSPECIFIED",
            "NONE",
            "BETWEEN_EACH_COLUMN",
        ]
        | UnsetType = UNSET,
        content_direction: Literal[
            "CONTENT_DIRECTION_UNSPECIFIED",
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
        ]
        | UnsetType = UNSET,
        section_type: Literal[
            "SECTION_TYPE_UNSPECIFIED",
            "CONTINUOUS",
            "NEXT_PAGE",
        ]
        | UnsetType = UNSET,
        default_header_id: str | UnsetType = UNSET,
        default_footer_id: str | UnsetType = UNSET,
        even_page_header_id: str | UnsetType = UNSET,
        even_page_footer_id: str | UnsetType = UNSET,
        first_page_header_id: str | UnsetType = UNSET,
        first_page_footer_id: str | UnsetType = UNSET,
        use_first_page_header_footer: bool | UnsetType = UNSET,
        flip_page_orientation: bool | UnsetType = UNSET,
        page_number_start: int | UnsetType = UNSET,
        margin_top: Dimension | UnsetType = UNSET,
        margin_bottom: Dimension | UnsetType = UNSET,
        margin_left: Dimension | UnsetType = UNSET,
        margin_right: Dimension | UnsetType = UNSET,
        margin_header: Dimension | UnsetType = UNSET,
        margin_footer: Dimension | UnsetType = UNSET,
    ) -> None:
        self.columns = columns
        self.column_separator_style = column_separator_style
        self.content_direction = content_direction
        self.section_type = section_type
        self.default_header_id = default_header_id
        self.default_footer_id = default_footer_id
        self.even_page_header_id = even_page_header_id
        self.even_page_footer_id = even_page_footer_id
        self.first_page_header_id = first_page_header_id
        self.first_page_footer_id = first_page_footer_id
        self.use_first_page_header_footer = use_first_page_header_footer
        self.flip_page_orientation = flip_page_orientation
        self.page_number_start = page_number_start
        self.margin_top = margin_top
        self.margin_bottom = margin_bottom
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_header = margin_header
        self.margin_footer = margin_footer


class SectionBreak(StructuralElement):
    def __init__(self, *, style: SectionStyle) -> None:
        self.style = style
