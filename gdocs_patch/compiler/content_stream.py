from dataclasses import dataclass, field

from gdocs_patch.models import (
    UNSET,
    Bullet,
    BulletPreset,
    Dimension,
    ListDefinition,
    ParagraphStyle,
    SectionStyle,
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
class TextUnit(ContentUnit):
    content: str
    text_style: TextStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


@dataclass(frozen=True, kw_only=True)
class OpaqueUnit(ContentUnit):
    key: str
    width: int
    is_inline: bool

    @property
    def utf16_width(self) -> int:
        return self.width


@dataclass(frozen=True, kw_only=True)
class PageBreakUnit(ContentUnit):
    text_style: TextStyle | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class EquationUnit(ContentUnit):
    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class SectionBreakUnit(ContentUnit):
    style: SectionStyle

    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class ParagraphBoundary(ContentUnit):
    text_style: TextStyle | UnsetType = UNSET
    paragraph_style: ParagraphStyle | UnsetType = UNSET
    bullet: Bullet | BulletPreset | UnsetType = UNSET
    list_definition: ListDefinition | UnsetType = UNSET

    @property
    def utf16_width(self) -> int:
        return 1


@dataclass(frozen=True, kw_only=True)
class ContentStream:
    items: list[ContentUnit]
    # The origin locates this stream but is not part of its semantic content.
    utf16_start_index: int = field(default=0, compare=False)

    @property
    def utf16_width(self) -> int:
        return sum(item.utf16_width for item in self.items)

    def utf16_index(self, position: int) -> int:
        return self.utf16_start_index + sum(
            item.utf16_width for item in self.items[:position]
        )

    def comparison_values(self) -> list[tuple[str, object]]:
        values: list[tuple[str, object]] = []
        for position, item in enumerate(self.items):
            if isinstance(item, TextUnit):
                values.append(("text", item.content))
            elif isinstance(item, PageBreakUnit):
                values.append(("page_break", ""))
            elif isinstance(item, EquationUnit):
                values.append(("equation", ""))
            elif isinstance(item, OpaqueUnit):
                values.append(("opaque", item.key))
            elif isinstance(item, SectionBreakUnit):
                values.append(("section_break", ""))
            elif isinstance(item, ParagraphBoundary):
                boundary_type = (
                    "terminal_paragraph_boundary"
                    if position == len(self.items) - 1
                    else "paragraph_boundary"
                )
                values.append((boundary_type, ""))
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
        return max((len(row.cells) for row in self.rows), default=0)

    def cell_content_offset(self, *, row_index: int, cell_index: int) -> int:
        return (
            1
            + sum(row.utf16_width for row in self.rows[:row_index])
            + 1
            + sum(cell.utf16_width for cell in self.rows[row_index].cells[:cell_index])
            + 1
        )
