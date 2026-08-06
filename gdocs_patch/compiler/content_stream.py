from dataclasses import dataclass
from typing import Literal

from gdocs_patch.models import (
    UNSET,
    Bullet,
    Dimension,
    ParagraphStyle,
    TableCellStyle,
    TableColumn,
    TextStyle,
    UnsetType,
)


class ContentUnit:
    @property
    def utf16_width(self) -> int:
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class BulletPreset:
    preset: Literal[
        "BULLET_GLYPH_PRESET_UNSPECIFIED",
        "BULLET_DISC_CIRCLE_SQUARE",
        "BULLET_DIAMONDX_ARROW3D_SQUARE",
        "BULLET_CHECKBOX",
        "BULLET_ARROW_DIAMOND_DISC",
        "BULLET_STAR_CIRCLE_SQUARE",
        "BULLET_ARROW3D_CIRCLE_SQUARE",
        "BULLET_LEFTTRIANGLE_DIAMOND_DISC",
        "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE",
        "BULLET_DIAMOND_CIRCLE_SQUARE",
        "NUMBERED_DECIMAL_ALPHA_ROMAN",
        "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
        "NUMBERED_DECIMAL_NESTED",
        "NUMBERED_UPPERALPHA_ALPHA_ROMAN",
        "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
        "NUMBERED_ZERODECIMAL_ALPHA_ROMAN",
    ]
    nesting_level: int = 0


@dataclass(frozen=True, kw_only=True)
class TextUnit(ContentUnit):
    content: str
    text_style: TextStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


@dataclass(frozen=True, kw_only=True)
class EquationUnit(ContentUnit):
    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class ParagraphBoundary(ContentUnit):
    text_style: TextStyle | UnsetType = UNSET
    paragraph_style: ParagraphStyle | UnsetType = UNSET
    bullet: Bullet | BulletPreset | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class ContentStream:
    items: list[ContentUnit]

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)

    def utf16_index(self, position: int, *, start_index: int = 0) -> int:
        return start_index + sum(item.utf16_width for item in self.items[:position])

    def comparison_values(self) -> list[tuple[str, object]]:
        values: list[tuple[str, object]] = []
        for item in self.items:
            if isinstance(item, TextUnit):
                values.append(("text", item.content))
            elif isinstance(item, EquationUnit):
                values.append(("equation", ""))
            elif isinstance(item, ParagraphBoundary):
                values.append(("paragraph_boundary", ""))
            elif isinstance(item, TableUnit):
                values.append(
                    (
                        "table",
                        item.table_key if item.table_key is not None else id(item),
                    )
                )
        return values


@dataclass(frozen=True, kw_only=True)
class TableCellUnit:
    cell_key: str | None = None
    content: ContentStream
    row_span: int = 1
    column_span: int = 1
    style: TableCellStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1 + self.content.utf16_width


@dataclass(frozen=True, kw_only=True)
class TableRowUnit:
    row_key: str | None = None
    cells: list[TableCellUnit]
    min_height: Dimension | UnsetType = UNSET
    prevent_overflow: bool | UnsetType = UNSET
    is_header: bool | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1 + sum(cell.utf16_width for cell in self.cells)


@dataclass(frozen=True, kw_only=True)
class TableUnit(ContentUnit):
    table_key: str | None = None
    rows: list[TableRowUnit]
    column_properties: list[TableColumn] | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 2 + sum(row.utf16_width for row in self.rows)

    @property
    def column_count(self) -> int:
        return max(
            (sum(cell.column_span for cell in row.cells) for row in self.rows),
            default=0,
        )

    def cell_content_offset(self, *, row_index: int, cell_index: int) -> int:
        return (
            1
            + sum(row.utf16_width for row in self.rows[:row_index])
            + 1
            + sum(cell.utf16_width for cell in self.rows[row_index].cells[:cell_index])
            + 1
        )
