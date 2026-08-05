from typing import Literal, cast

from .base import UNSET, Color, Dimension, Model, TreeNode, UnsetType
from .document import StructuralElement


class TableCellBorder(Model):
    def __init__(
        self,
        *,
        color: Color | None,
        width: Dimension,
        dash_style: Literal[
            "DASH_STYLE_UNSPECIFIED",
            "SOLID",
            "DOT",
            "DASH",
        ],
    ) -> None:
        self.color = color
        self.width = width
        self.dash_style = dash_style


class TableCellStyle(Model):
    def __init__(
        self,
        *,
        row_span: int = 1,
        column_span: int = 1,
        background_color: Color | None | UnsetType = UNSET,
        border_left: TableCellBorder | UnsetType = UNSET,
        border_right: TableCellBorder | UnsetType = UNSET,
        border_top: TableCellBorder | UnsetType = UNSET,
        border_bottom: TableCellBorder | UnsetType = UNSET,
        padding_left: Dimension | UnsetType = UNSET,
        padding_right: Dimension | UnsetType = UNSET,
        padding_top: Dimension | UnsetType = UNSET,
        padding_bottom: Dimension | UnsetType = UNSET,
        content_alignment: Literal[
            "CONTENT_ALIGNMENT_UNSPECIFIED",
            "CONTENT_ALIGNMENT_UNSUPPORTED",
            "TOP",
            "MIDDLE",
            "BOTTOM",
        ]
        | UnsetType = UNSET,
    ) -> None:
        if row_span <= 0:
            raise ValueError("row_span must be positive")
        if column_span <= 0:
            raise ValueError("column_span must be positive")
        self.row_span = row_span
        self.column_span = column_span
        self.background_color = background_color
        self.border_left = border_left
        self.border_right = border_right
        self.border_top = border_top
        self.border_bottom = border_bottom
        self.padding_left = padding_left
        self.padding_right = padding_right
        self.padding_top = padding_top
        self.padding_bottom = padding_bottom
        self.content_alignment = content_alignment


class TableCell(TreeNode):
    def __init__(
        self,
        *,
        content: list[StructuralElement],
        style: TableCellStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        for child in content:
            self.add_child(child)
        self.style = style

    @property
    def content(self) -> list[StructuralElement]:
        return cast("list[StructuralElement]", self.children)


class TableRow(TreeNode):
    def __init__(
        self,
        *,
        cells: list[TableCell],
        min_height: Dimension | UnsetType = UNSET,
        prevent_overflow: bool | UnsetType = UNSET,
        is_header: bool | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        for child in cells:
            self.add_child(child)
        self.min_height = min_height
        self.prevent_overflow = prevent_overflow
        self.is_header = is_header

    @property
    def cells(self) -> list[TableCell]:
        return cast("list[TableCell]", self.children)


class TableColumn(Model):
    def __init__(
        self,
        *,
        width_type: Literal[
            "WIDTH_TYPE_UNSPECIFIED",
            "EVENLY_DISTRIBUTED",
            "FIXED_WIDTH",
        ],
        width: Dimension | UnsetType = UNSET,
    ) -> None:
        if width_type == "FIXED_WIDTH" and width is UNSET:
            raise ValueError("width must be set when width_type is FIXED_WIDTH")
        if width_type != "FIXED_WIDTH" and width is not UNSET:
            raise ValueError("width must be unset unless width_type is FIXED_WIDTH")
        self.width_type = width_type
        self.width = width


class Table(StructuralElement):
    def __init__(
        self,
        *,
        rows: list[TableRow],
        column_styles: list[TableColumn] | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        for child in rows:
            self.add_child(child)
        self.column_styles = column_styles

    @property
    def rows(self) -> list[TableRow]:
        return cast("list[TableRow]", self.children)
