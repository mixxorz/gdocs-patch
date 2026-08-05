from typing import Literal

from .base import UNSET, Dimension, Model, UnsetType
from .paragraph import TextStyle


class ListLevel(Model):
    def __init__(
        self,
        *,
        glyph_format: str,
        glyph_type: Literal[
            "GLYPH_TYPE_UNSPECIFIED",
            "NONE",
            "DECIMAL",
            "ZERO_DECIMAL",
            "UPPER_ALPHA",
            "ALPHA",
            "UPPER_ROMAN",
            "ROMAN",
        ]
        | UnsetType = UNSET,
        glyph_symbol: str | UnsetType = UNSET,
        alignment: Literal[
            "BULLET_ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
        ] = "BULLET_ALIGNMENT_UNSPECIFIED",
        indent_first_line: Dimension | UnsetType = UNSET,
        indent_start: Dimension | UnsetType = UNSET,
        start_number: int = 0,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        if (glyph_type is UNSET) == (glyph_symbol is UNSET):
            raise ValueError("exactly one of glyph_type and glyph_symbol must be set")
        self.glyph_format = glyph_format
        self.glyph_type = glyph_type
        self.glyph_symbol = glyph_symbol
        self.alignment = alignment
        self.indent_first_line = indent_first_line
        self.indent_start = indent_start
        self.start_number = start_number
        self.text_style = text_style


class ListDefinition(Model):
    def __init__(self, *, levels: list[ListLevel]) -> None:
        self.levels = levels
