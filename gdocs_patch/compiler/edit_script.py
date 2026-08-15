from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import Literal, cast

from gdocs_patch.models import (
    UNSET,
    Bullet,
    Dimension,
    ListDefinition,
    ParagraphStyle,
    SectionStyle,
    TableCellStyle,
    TableColumn,
    TextStyle,
    UnsetType,
)

from .bullets import closest_preset, exact_preset
from .content_stream import (
    BulletPreset,
    ContentStream,
    ContentUnit,
    EquationUnit,
    OpaqueUnit,
    PageBreakUnit,
    ParagraphBoundary,
    SectionBreakUnit,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
)


class UnsupportedTransformation(Exception):
    pass


@dataclass(frozen=True, kw_only=True)
class EditScriptContext:
    allow_bullet_normalization: bool = False
    prevent_table_indent_inheritance: bool = True
    inside_table: bool = False
    inside_non_body_segment: bool = False


DEFAULT_EDIT_SCRIPT_CONTEXT = EditScriptContext()


def writable_paragraph_style(
    style: ParagraphStyle | UnsetType,
) -> tuple[object, ...]:
    paragraph_style = style if isinstance(style, ParagraphStyle) else ParagraphStyle()
    return (
        paragraph_style.named_style_type,
        paragraph_style.alignment,
        paragraph_style.direction,
        paragraph_style.line_spacing,
        paragraph_style.spacing_mode,
        paragraph_style.space_above,
        paragraph_style.space_below,
        paragraph_style.indent_first_line,
        paragraph_style.indent_start,
        paragraph_style.indent_end,
        paragraph_style.keep_lines_together,
        paragraph_style.keep_with_next,
        paragraph_style.avoid_widow_and_orphan,
        paragraph_style.page_break_before,
        paragraph_style.border_between,
        paragraph_style.border_top,
        paragraph_style.border_bottom,
        paragraph_style.border_left,
        paragraph_style.border_right,
        paragraph_style.shading_color,
    )


def writable_section_style(style: SectionStyle) -> tuple[object, ...]:
    return (
        style.columns,
        style.column_separator_style,
        style.content_direction,
        style.use_first_page_header_footer,
        style.flip_page_orientation,
        style.page_number_start,
        style.margin_top,
        style.margin_bottom,
        style.margin_left,
        style.margin_right,
        style.margin_header,
        style.margin_footer,
    )


def writable_table_cell_style(
    style: TableCellStyle | UnsetType,
) -> tuple[object, ...]:
    cell_style = style if isinstance(style, TableCellStyle) else TableCellStyle()
    return (
        cell_style.background_color,
        cell_style.border_left,
        cell_style.border_right,
        cell_style.border_top,
        cell_style.border_bottom,
        cell_style.padding_left,
        cell_style.padding_right,
        cell_style.padding_top,
        cell_style.padding_bottom,
        cell_style.content_alignment,
    )


class Edit:
    """Marker type for operations in an edit script."""


@dataclass(frozen=True, kw_only=True)
class InsertText(Edit):
    index: int
    text: str


@dataclass(frozen=True, kw_only=True)
class InsertPageBreak(Edit):
    index: int


@dataclass(frozen=True, kw_only=True)
class InsertTable(Edit):
    index: int
    rows: int
    columns: int
    preceding_boundary: Literal["INSERTED", "RETAINED"]
    prevent_indent_inheritance: bool = False


@dataclass(frozen=True, kw_only=True)
class InsertSectionBreak(Edit):
    index: int
    section_type: Literal[
        "SECTION_TYPE_UNSPECIFIED",
        "CONTINUOUS",
        "NEXT_PAGE",
    ]
    preceding_boundary: Literal["INSERTED", "RETAINED"]


@dataclass(frozen=True, kw_only=True)
class DeleteSectionBreak(Edit):
    index: int


@dataclass(frozen=True, kw_only=True)
class ApplySectionStyle(Edit):
    start_index: int
    end_index: int
    section_style: SectionStyle


@dataclass(frozen=True, kw_only=True)
class InsertTableRow(Edit):
    table_start_index: int
    row_index: int
    column_index: int
    insert_below: bool


@dataclass(frozen=True, kw_only=True)
class InsertTableColumn(Edit):
    table_start_index: int
    row_index: int
    column_index: int
    insert_right: bool


@dataclass(frozen=True, kw_only=True)
class DeleteTableRow(Edit):
    table_start_index: int
    row_index: int
    column_index: int


@dataclass(frozen=True, kw_only=True)
class DeleteTableColumn(Edit):
    table_start_index: int
    row_index: int
    column_index: int


@dataclass(frozen=True, kw_only=True)
class MergeTableCells(Edit):
    table_start_index: int
    row_index: int
    column_index: int
    row_span: int
    column_span: int


@dataclass(frozen=True, kw_only=True)
class UnmergeTableCells(Edit):
    table_start_index: int
    row_index: int
    column_index: int
    row_span: int
    column_span: int


@dataclass(frozen=True, kw_only=True)
class DeleteContent(Edit):
    start_index: int
    end_index: int


@dataclass(frozen=True, kw_only=True)
class BulletParagraph:
    start_index: int
    end_index: int
    nesting_level: int


@dataclass(frozen=True, kw_only=True)
class ApplyBulletRun(Edit):
    paragraphs: tuple[BulletParagraph, ...]
    preset: str


@dataclass(frozen=True, kw_only=True)
class DeleteParagraphBullets(Edit):
    start_index: int
    end_index: int


@dataclass(frozen=True, kw_only=True)
class ApplyTextStyle(Edit):
    start_index: int
    end_index: int
    text_style: TextStyle | UnsetType


@dataclass(frozen=True, kw_only=True)
class ApplyParagraphStyle(Edit):
    start_index: int
    end_index: int
    paragraph_style: ParagraphStyle | UnsetType
    inside_table: bool = False


@dataclass(frozen=True, kw_only=True)
class ApplyTableColumnProperties(Edit):
    table_start_index: int
    column_index: int
    column_properties: TableColumn | UnsetType


@dataclass(frozen=True, kw_only=True)
class ApplyTableRowStyle(Edit):
    table_start_index: int
    row_index: int
    min_height: Dimension | UnsetType
    prevent_overflow: bool | UnsetType
    is_header: bool | UnsetType


@dataclass(frozen=True, kw_only=True)
class ApplyTableCellStyle(Edit):
    table_start_index: int
    row_index: int
    column_index: int
    row_span: int
    column_span: int
    cell_style: TableCellStyle | UnsetType


class EditScript:
    def __init__(
        self,
        *,
        edits: list[Edit],
    ) -> None:
        self.edits = edits


Opcode = tuple[str, int, int, int, int]
TableAxisOperation = tuple[Literal["delete", "insert"], int]


def match_content(*, source: ContentStream, target: ContentStream) -> Sequence[Opcode]:
    return SequenceMatcher(
        a=source.comparison_values(),
        b=target.comparison_values(),
        autojunk=False,
    ).get_opcodes()


def _plan_table_axis_operations(
    *,
    source_count: int,
    deleted_source_indices: Sequence[int],
    new_target_indices: Sequence[int],
) -> list[TableAxisOperation]:
    deleted_indices = list(deleted_source_indices)
    deferred_anchor = (
        source_count > 0
        and len(deleted_indices) == source_count
        and bool(new_target_indices)
    )
    if deferred_anchor:
        deleted_indices = deleted_indices[1:]

    operations: list[TableAxisOperation] = [
        ("delete", index) for index in reversed(deleted_indices)
    ]
    operations.extend(("insert", index) for index in new_target_indices)
    if deferred_anchor:
        operations.append(("delete", len(new_target_indices)))
    return operations


def compile_inserted_table(
    *,
    table: TableUnit,
    source_table_start_index: int,
    target_table_start_index: int,
    preceding_boundary: Literal["INSERTED", "RETAINED"],
    context: EditScriptContext,
) -> list[Edit]:
    table_context = replace(context, inside_table=True)
    edits: list[Edit] = [
        InsertTable(
            index=source_table_start_index,
            rows=len(table.rows),
            columns=table.column_count,
            preceding_boundary=preceding_boundary,
            prevent_indent_inheritance=(
                context.prevent_table_indent_inheritance
                and preceding_boundary == "RETAINED"
            ),
        )
    ]
    # Google creates an inserted table as a blank grid, with one empty paragraph
    # in every cell. Since the cell content requests run against that initial
    # grid, use an equivalent blank table to calculate their insertion indices.
    blank_table_unit = TableUnit(
        rows=[
            TableRowUnit(
                cells=[
                    TableCellUnit(
                        content=ContentStream(items=[ParagraphBoundary()]),
                    )
                    for _column_index in range(table.column_count)
                ]
            )
            for _row in table.rows
        ]
    )
    cells = [
        (row_index, cell_index, cell)
        for row_index, row in enumerate(table.rows)
        for cell_index, cell in enumerate(row.cells)
    ]
    for row_index, cell_index, cell in reversed(cells):
        cell_script = generate_edit_script(
            source=ContentStream(
                items=[ParagraphBoundary()],
                utf16_start_index=(
                    source_table_start_index
                    + blank_table_unit.cell_content_offset(
                        row_index=row_index,
                        cell_index=cell_index,
                    )
                ),
            ),
            target=ContentStream(
                items=cell.content.items,
                utf16_start_index=(
                    target_table_start_index
                    + table.cell_content_offset(
                        row_index=row_index,
                        cell_index=cell_index,
                    )
                ),
            ),
            context=table_context,
        )
        edits.extend(cell_script.edits)

    if isinstance(table.column_properties, list):
        for column_index, column_properties in enumerate(table.column_properties):
            edits.append(
                ApplyTableColumnProperties(
                    table_start_index=target_table_start_index,
                    column_index=column_index,
                    column_properties=column_properties,
                )
            )
    for row_index, row in enumerate(table.rows):
        if (row.min_height, row.prevent_overflow, row.is_header) != (
            UNSET,
            UNSET,
            UNSET,
        ):
            edits.append(
                ApplyTableRowStyle(
                    table_start_index=target_table_start_index,
                    row_index=row_index,
                    min_height=row.min_height,
                    prevent_overflow=row.prevent_overflow,
                    is_header=row.is_header,
                )
            )
        for cell_index, cell in enumerate(row.cells):
            if cell.style is not UNSET:
                edits.append(
                    ApplyTableCellStyle(
                        table_start_index=target_table_start_index,
                        row_index=row_index,
                        column_index=cell_index,
                        row_span=cell.row_span,
                        column_span=cell.column_span,
                        cell_style=cell.style,
                    )
                )
    return edits


def generate_table_edits(
    *,
    source: TableUnit,
    target: TableUnit,
    source_table_start_index: int,
    target_table_start_index: int,
    context: EditScriptContext,
) -> list[Edit]:
    """Generate the edits needed to update one retained table.

    Row and cell keys tell us which parts of the source table survived in the
    target. We first change the table's structure, then update cell content, and
    finally apply table formatting after the target shape is in place.
    """

    table_context = replace(context, inside_table=True)

    # Match rows
    # ----------
    # Group source rows by key before walking the target. Each key owns a queue
    # because duplicate keys are allowed. Taking rows from the front preserves
    # source order and ensures that one source row cannot be matched twice.
    available_source_rows_by_key: dict[
        str | None,
        deque[tuple[int, TableRowUnit]],
    ] = {}
    for source_row_index, source_row_unit in enumerate(source.rows):
        available_source_rows_by_key.setdefault(
            source_row_unit.row_key,
            deque(),
        ).append((source_row_index, source_row_unit))

    source_rows_by_target: dict[int, TableRowUnit] = {}
    new_row_indices: list[int] = []
    for target_row_index, target_row_unit in enumerate(target.rows):
        matching_source_rows = available_source_rows_by_key.get(target_row_unit.row_key)
        if matching_source_rows:
            _source_row_index, source_row_unit = matching_source_rows.popleft()
            source_rows_by_target[target_row_index] = source_row_unit
        else:
            new_row_indices.append(target_row_index)

    available_source_rows = sorted(
        (
            source_row
            for source_rows in available_source_rows_by_key.values()
            for source_row in source_rows
        ),
        key=lambda source_row: source_row[0],
    )

    # Reconcile rows
    # --------------
    # Google removes the table when its last row is deleted. The shared axis
    # planner keeps one temporary source anchor during a complete replacement.
    edits: list[Edit] = []
    for operation, row_index in _plan_table_axis_operations(
        source_count=len(source.rows),
        deleted_source_indices=[
            source_row_index for source_row_index, _source_row in available_source_rows
        ],
        new_target_indices=new_row_indices,
    ):
        if operation == "delete":
            edits.append(
                DeleteTableRow(
                    table_start_index=source_table_start_index,
                    row_index=row_index,
                    column_index=0,
                )
            )
        else:
            edits.append(
                InsertTableRow(
                    table_start_index=source_table_start_index,
                    row_index=max(0, row_index - 1),
                    column_index=0,
                    insert_below=row_index > 0,
                )
            )

    # Match cells
    # -----------
    # Once rows are aligned, repeat the same key-based matching within each
    # retained row. Every cell in a new row is new by definition.
    matched_cells: list[tuple[int, int, TableCellUnit, TableCellUnit]] = []
    new_cells: list[tuple[int, int, TableCellUnit]] = []
    deleted_cell_indices: dict[int, list[int]] = {}
    for target_row_index, target_row in enumerate(target.rows):
        source_row = source_rows_by_target.get(target_row_index)
        if source_row is None:
            new_cells.extend(
                (target_row_index, cell_index, cell)
                for cell_index, cell in enumerate(target_row.cells)
            )
            continue

        available_source_cells = list(enumerate(source_row.cells))
        for target_cell_index, target_cell in enumerate(target_row.cells):
            source_cell = next(
                (
                    item
                    for item in available_source_cells
                    if item[1].cell_key == target_cell.cell_key
                ),
                None,
            )
            if source_cell is None:
                new_cells.append((target_row_index, target_cell_index, target_cell))
            else:
                available_source_cells.remove(source_cell)
                matched_cells.append(
                    (
                        target_row_index,
                        target_cell_index,
                        source_cell[1],
                        target_cell,
                    )
                )
        deleted_cell_indices[target_row_index] = [
            cell_index for cell_index, _cell in available_source_cells
        ]

    column_reference_row_index = next(iter(source_rows_by_target), None)

    # Reconcile columns
    # -----------------
    # A retained row supplies the cell identities for table-wide column edits.
    # Without one, only the source and target dimensions can be reconciled.
    column_delta = target.column_count - source.column_count
    if column_reference_row_index is not None:
        deleted_column_indices = deleted_cell_indices[column_reference_row_index]
        new_column_indices = [
            cell_index
            for row_index, cell_index, _cell in new_cells
            if row_index == column_reference_row_index
        ]
        column_location_row_index = column_reference_row_index
    else:
        deleted_column_indices = (
            list(range(target.column_count, source.column_count))
            if column_delta < 0
            else []
        )
        new_column_indices = (
            list(range(source.column_count, target.column_count))
            if column_delta > 0
            else []
        )
        column_location_row_index = 0

    for operation, column_index in _plan_table_axis_operations(
        source_count=source.column_count,
        deleted_source_indices=deleted_column_indices,
        new_target_indices=new_column_indices,
    ):
        if operation == "delete":
            edits.append(
                DeleteTableColumn(
                    table_start_index=source_table_start_index,
                    row_index=column_location_row_index,
                    column_index=column_index,
                )
            )
        else:
            edits.append(
                InsertTableColumn(
                    table_start_index=source_table_start_index,
                    row_index=column_location_row_index,
                    column_index=max(0, column_index - 1),
                    insert_right=column_index > 0,
                )
            )

    # Merge and unmerge cells
    # -----------------------
    # A larger target span means neighboring cells must be merged. A smaller
    # target span means the source cell must be split back into individual cells.
    # Remember newly merged cells because their content is governed by the merge
    # operation and should not also be edited using the old cell layout.
    merged_target_cell_ids: set[int] = set()
    for row_index, cell_index, source_cell, target_cell in matched_cells:
        if (
            target_cell.row_span > source_cell.row_span
            or target_cell.column_span > source_cell.column_span
        ):
            edits.append(
                MergeTableCells(
                    table_start_index=source_table_start_index,
                    row_index=row_index,
                    column_index=cell_index,
                    row_span=target_cell.row_span,
                    column_span=target_cell.column_span,
                )
            )
            for merged_row in target.rows[row_index : row_index + target_cell.row_span]:
                for merged_cell in merged_row.cells[
                    cell_index : cell_index + target_cell.column_span
                ]:
                    merged_target_cell_ids.add(id(merged_cell))
        elif (
            source_cell.row_span > target_cell.row_span
            or source_cell.column_span > target_cell.column_span
        ):
            edits.append(
                UnmergeTableCells(
                    table_start_index=source_table_start_index,
                    row_index=row_index,
                    column_index=cell_index,
                    row_span=source_cell.row_span,
                    column_span=source_cell.column_span,
                )
            )

    # Locate cells after the structural edits
    # ----------------------------------------
    # Row, column, merge, and unmerge requests run before any cell content is
    # changed. Build the table shape that those requests leave behind so the
    # content edits use the indices that exist when they actually run. Retained
    # cells still contain their source content, while newly created cells contain
    # the one empty paragraph Google gives them.
    source_cells_by_target = {
        (row_index, cell_index): source_cell
        for row_index, cell_index, source_cell, _target_cell in matched_cells
    }
    empty_cell_content = ContentStream(items=[ParagraphBoundary()])
    table_before_content_edits = TableUnit(
        rows=[
            TableRowUnit(
                cells=[
                    TableCellUnit(
                        content=(
                            source_cells_by_target[(row_index, cell_index)].content
                            if (row_index, cell_index) in source_cells_by_target
                            else empty_cell_content
                        ),
                        row_span=target_cell.row_span,
                        column_span=target_cell.column_span,
                    )
                    for cell_index, target_cell in enumerate(target_row.cells)
                ]
            )
            for row_index, target_row in enumerate(target.rows)
        ]
    )

    # Update cell content
    # -------------------
    # Every new Google cell starts with one empty paragraph, while retained cells
    # still contain their source content. Run both kinds through the normal
    # content compiler, working from right to left so an edit cannot move a cell
    # that we have not processed yet.
    cell_content_changes = [
        (row_index, cell_index, empty_cell_content, target_cell.content)
        for row_index, cell_index, target_cell in new_cells
    ]
    cell_content_changes.extend(
        (row_index, cell_index, source_cell.content, target_cell.content)
        for row_index, cell_index, source_cell, target_cell in matched_cells
        if id(target_cell) not in merged_target_cell_ids
    )
    cell_content_changes.sort(
        key=lambda change: (change[0], change[1]),
        reverse=True,
    )

    for row_index, cell_index, source_content, target_content in cell_content_changes:
        source_content = ContentStream(
            items=source_content.items,
            utf16_start_index=(
                source_table_start_index
                + table_before_content_edits.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                )
            ),
        )
        target_content = ContentStream(
            items=target_content.items,
            utf16_start_index=(
                target_table_start_index
                + target.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                )
            ),
        )
        cell_script = generate_edit_script(
            source=source_content,
            target=target_content,
            context=table_context,
        )

        edits.extend(cell_script.edits)

    # Column formatting
    # -----------------
    # If the number of columns changed, reapply every target column's properties
    # because source and target positions may no longer line up. Otherwise only
    # columns whose writable properties changed need an edit.
    source_column_properties = (
        source.column_properties if isinstance(source.column_properties, list) else None
    )
    target_column_properties = (
        target.column_properties if isinstance(target.column_properties, list) else None
    )
    columns_changed = source.column_count != target.column_count
    if source_column_properties is not None or target_column_properties is not None:
        for column_index in range(target.column_count):
            source_properties = (
                source_column_properties[column_index]
                if source_column_properties is not None
                and column_index < len(source_column_properties)
                else UNSET
            )
            target_properties = (
                target_column_properties[column_index]
                if target_column_properties is not None
                and column_index < len(target_column_properties)
                else UNSET
            )
            if columns_changed or source_properties != target_properties:
                edits.append(
                    ApplyTableColumnProperties(
                        table_start_index=target_table_start_index,
                        column_index=column_index,
                        column_properties=target_properties,
                    )
                )

    # Row formatting
    # --------------
    # New rows have no source formatting to compare. For retained rows, emit an
    # edit only when one of the writable row-style values changed.
    for target_row_index, target_row in enumerate(target.rows):
        source_row = source_rows_by_target.get(target_row_index)
        source_row_style = (
            (
                source_row.min_height,
                source_row.prevent_overflow,
                source_row.is_header,
            )
            if source_row is not None
            else (UNSET, UNSET, UNSET)
        )
        target_row_style = (
            target_row.min_height,
            target_row.prevent_overflow,
            target_row.is_header,
        )
        if source_row_style != target_row_style:
            edits.append(
                ApplyTableRowStyle(
                    table_start_index=target_table_start_index,
                    row_index=target_row_index,
                    min_height=target_row.min_height,
                    prevent_overflow=target_row.prevent_overflow,
                    is_header=target_row.is_header,
                )
            )

    # Cell formatting
    # ---------------
    # Compare each target cell with the source cell matched earlier. Google keeps
    # placeholder cells after a merge, so the cell's list position is also its
    # column index.
    for row_index, row in enumerate(target.rows):
        for cell_index, target_cell in enumerate(row.cells):
            source_cell = source_cells_by_target.get((row_index, cell_index))
            source_style = source_cell.style if source_cell is not None else UNSET
            if writable_table_cell_style(source_style) != writable_table_cell_style(
                target_cell.style
            ):
                edits.append(
                    ApplyTableCellStyle(
                        table_start_index=target_table_start_index,
                        row_index=row_index,
                        column_index=cell_index,
                        row_span=target_cell.row_span,
                        column_span=target_cell.column_span,
                        cell_style=target_cell.style,
                    )
                )

    return edits


def is_insert_text_unit(unit: ContentUnit) -> bool:
    return isinstance(unit, (TextUnit, ParagraphBoundary))


def is_inline_paragraph_unit(unit: ContentUnit) -> bool:
    return isinstance(unit, (TextUnit, PageBreakUnit, EquationUnit)) or (
        isinstance(unit, OpaqueUnit) and unit.is_inline
    )


def generate_edit_script(
    *,
    source: ContentStream,
    target: ContentStream,
    context: EditScriptContext = DEFAULT_EDIT_SCRIPT_CONTEXT,
) -> EditScript:
    """Describe how to change source content and formatting into the target.

    SequenceMatcher aligns the source and target as flat content units. This
    function first turns that alignment into content edits that use source
    UTF-16 indices. Once those edits have produced the target shape, it emits
    bullets and styles using target UTF-16 indices. The separation is important
    because an insertion or deletion invalidates the other document's coordinates.

    In this function, a unit is one ContentStream entry. A stream position
    locates a unit, a stream range spans units, and a UTF-16 index locates
    content in Google Docs.
    """

    # ParagraphBoundary represents the final newline of a paragraph, but most
    # paragraph operations need the complete paragraph's UTF-16 range. Walk the
    # target once and remember the range ending at each boundary. Later code can
    # move from a matched boundary to its paragraph's UTF-16 range.
    target_paragraph_utf16_range_by_target_pos: dict[int, tuple[int, int]] = {}
    paragraph_start_utf16_index = target.utf16_start_index
    target_utf16_index = target.utf16_start_index
    for target_pos, target_unit in enumerate(target.items):
        target_utf16_index += target_unit.utf16_width
        if isinstance(target_unit, (TableUnit, SectionBreakUnit)) or (
            isinstance(target_unit, OpaqueUnit) and not target_unit.is_inline
        ):
            paragraph_start_utf16_index = target_utf16_index
        elif isinstance(target_unit, ParagraphBoundary):
            target_paragraph_utf16_range_by_target_pos[target_pos] = (
                paragraph_start_utf16_index,
                target_utf16_index,
            )
            paragraph_start_utf16_index = target_utf16_index

    edits: list[Edit] = []
    # Each opcode identifies a source stream range and the target stream range
    # that should replace it. Styles are absent from the compared values, so
    # equal content remains aligned even when only its formatting changed.
    opcodes = match_content(source=source, target=target)

    # Equations can be retained or deleted, but the batchUpdate API has no
    # request that creates one. Reject the transformation before emitting a
    # partial script if an inserted target stream range contains an equation.
    for (
        tag,
        _source_start_pos,
        _source_end_pos,
        target_start_pos,
        target_end_pos,
    ) in opcodes:
        if tag in {"insert", "replace"}:
            target_range = target.items[target_start_pos:target_end_pos]
            if any(
                isinstance(target_unit, EquationUnit) for target_unit in target_range
            ):
                raise UnsupportedTransformation(
                    "Google Docs cannot insert Equation elements"
                )
            opaque_elements = sorted(
                {
                    (
                        f"{target_unit.element_type} ({target_unit.object_identity})"
                        if target_unit.object_identity is not None
                        else target_unit.element_type
                    )
                    for target_unit in target_range
                    if isinstance(target_unit, OpaqueUnit)
                }
            )
            if opaque_elements:
                elements = ", ".join(opaque_elements)
                raise UnsupportedTransformation(
                    f"cannot insert unsupported Google Docs element(s): {elements}"
                )
            if any(
                isinstance(target_unit, PageBreakUnit) for target_unit in target_range
            ):
                if context.inside_table or context.inside_non_body_segment:
                    raise UnsupportedTransformation(
                        "Google Docs can only insert a page break in the document body "
                        "(not in a table cell, header, footer, or footnote)"
                    )

    # Deleting a paragraph boundary joins the surrounding text into one
    # paragraph. Google keeps one side's paragraph style during that merge, and
    # it may not be the target style. Remember the surviving target paragraph so
    # its style is reapplied even if SequenceMatcher considered it unchanged.

    # These are stream positions of target ParagraphBoundary units whose
    # paragraph styles must be reapplied after a source boundary is deleted.
    forced_paragraph_style_positions: set[int] = set()
    forced_newline_text_style_positions: set[int] = set()
    for (
        tag,
        source_start_pos,
        source_end_pos,
        target_start_pos,
        _target_end_pos,
    ) in opcodes:
        if tag in {"delete", "replace"} and any(
            isinstance(source_unit, ParagraphBoundary)
            for source_unit in source.items[source_start_pos:source_end_pos]
        ):
            for target_pos in range(target_start_pos, len(target.items)):
                if isinstance(target.items[target_pos], ParagraphBoundary):
                    forced_paragraph_style_positions.add(target_pos)
                    break

    # How the index calculations work
    # -------------------------------
    # SequenceMatcher tells us where units appear in a ContentStream, but Google
    # expects every request to use UTF-16 indices. Whenever we need one of those
    # indices, ContentStream.utf16_index calculates it by adding up the widths of
    # the units that come before it. This lets us calculate each index directly
    # from the source or target stream instead of trying to keep a running cursor
    # in sync as we build the edit script.
    #
    # Content edits need to point into the document as it exists before any
    # requests run, so we calculate their indices from the source stream. We also
    # emit them from right to left, which prevents a later edit from shifting the
    # index needed by an earlier one. Once those edits have run, the document has
    # the same shape as the target, so bullet and style edits can use indices
    # calculated from the target stream.
    #
    # Inserting a new table uses both coordinate systems. The opcode tells us
    # where its target stream range should be inserted in the source. We start at
    # that source insertion index, then add the table's UTF-16 offset from the
    # beginning of the target stream range. That gives us the table's final
    # insertion index in the document.
    #
    # The loop below inspects the units covered by each opcode. Most equal units
    # need no content edit. Tables are the exception because their outer unit can
    # match while rows, cells, or cell content still need to change.
    inserted_structural_boundary_positions: set[int] = set()
    for opcode in reversed(opcodes):
        tag, source_start_pos, source_end_pos, target_start_pos, target_end_pos = opcode

        # Equal content
        # -------------
        # Equal text and paragraph boundaries are already correct, so there is
        # nothing to emit for them during the content phase. An equal TableUnit
        # only tells us that the same table was retained. Its rows, cells, and
        # cell content may still differ, so inspect the table's contents.
        if tag == "equal":
            source_units = source.items[source_start_pos:source_end_pos]
            target_units = target.items[target_start_pos:target_end_pos]
            for range_offset, (source_unit, target_unit) in enumerate(
                zip(source_units, target_units)
            ):
                source_pos = source_start_pos + range_offset
                target_pos = target_start_pos + range_offset
                if isinstance(source_unit, TableUnit) and isinstance(
                    target_unit, TableUnit
                ):
                    edits.extend(
                        generate_table_edits(
                            source=source_unit,
                            target=target_unit,
                            source_table_start_index=source.utf16_index(source_pos),
                            target_table_start_index=target.utf16_index(target_pos),
                            context=context,
                        )
                    )
            continue

        # Changed content
        # ---------------
        # Insert, delete, and replace opcodes do not align their source and
        # target units. Delete the complete source range once, then walk the
        # target range and create whatever units it contains.
        insertion_utf16_index = source.utf16_index(source_start_pos)
        if tag in {"delete", "replace"}:
            source_range = source.items[source_start_pos:source_end_pos]
            # Most changed ranges can go straight to deleteContentRange. A
            # SectionBreak cannot be deleted alone: Google requires its preceding
            # paragraph boundary to be removed with it. Keep that operation
            # semantic so lowering can insert temporary boundaries on both sides
            # and preserve the neighboring paragraph styles and bullets.
            if all(isinstance(unit, SectionBreakUnit) for unit in source_range):
                for source_pos in range(source_end_pos - 1, source_start_pos - 1, -1):
                    edits.append(
                        DeleteSectionBreak(index=source.utf16_index(source_pos))
                    )
            else:
                edits.append(
                    DeleteContent(
                        start_index=insertion_utf16_index,
                        end_index=source.utf16_index(source_end_pos),
                    )
                )

        # New content
        # -----------
        # After removing any replaced source content, build the target range
        # from left to right. Each pass handles one kind of content: text follows
        # the normal InsertText path, while a table goes to its own compiler.
        # Other content can get its own branch here when we support inserting it.
        target_range_start_utf16_index = target.utf16_index(target_start_pos)
        target_pos = target_start_pos
        while target_pos < target_end_pos:
            target_unit = target.items[target_pos]
            preceding_boundary: Literal["INSERTED", "RETAINED"] = "RETAINED"
            # Table and SectionBreak insertions create their own preceding
            # newline. When that boundary is part of this target range, consume
            # it with the structure instead of emitting a second newline through
            # InsertText. Its position is still recorded for the formatting pass.
            if (
                isinstance(target_unit, ParagraphBoundary)
                and target_pos + 1 < target_end_pos
                and isinstance(
                    target.items[target_pos + 1],
                    (TableUnit, SectionBreakUnit),
                )
            ):
                preceding_boundary = "INSERTED"
                inserted_structural_boundary_positions.add(target_pos)
                target_pos += 1
                target_unit = target.items[target_pos]

            if is_insert_text_unit(target_unit):
                text_start_pos = target_pos
                target_pos += 1
                # A TextUnit normally contains one character. Keep moving until
                # we reach something that InsertText cannot represent, then
                # insert the whole run at once instead of making one request for
                # every character.
                while target_pos < target_end_pos:
                    if is_insert_text_unit(target.items[target_pos]):
                        target_pos += 1
                        continue
                    break

                text_utf16_offset = (
                    target.utf16_index(text_start_pos) - target_range_start_utf16_index
                )
                text = "".join(
                    text_unit.content if isinstance(text_unit, TextUnit) else "\n"
                    for text_unit in target.items[text_start_pos:target_pos]
                )
                edits.append(
                    InsertText(
                        index=insertion_utf16_index + text_utf16_offset,
                        text=text,
                    )
                )
                continue

            if isinstance(target_unit, PageBreakUnit):
                page_break_utf16_offset = (
                    target.utf16_index(target_pos) - target_range_start_utf16_index
                )
                edits.append(
                    InsertPageBreak(
                        index=insertion_utf16_index + page_break_utf16_offset
                    )
                )
                target_pos += 1
                continue

            if isinstance(target_unit, TableUnit):
                table_utf16_offset = (
                    target.utf16_index(target_pos) - target_range_start_utf16_index
                )
                source_table_start_index = insertion_utf16_index + table_utf16_offset
                edits.extend(
                    compile_inserted_table(
                        table=target_unit,
                        source_table_start_index=source_table_start_index,
                        target_table_start_index=target.utf16_index(target_pos),
                        preceding_boundary=preceding_boundary,
                        context=context,
                    )
                )
                if (
                    context.prevent_table_indent_inheritance
                    and preceding_boundary == "RETAINED"
                    and target_pos > 0
                    and isinstance(target.items[target_pos - 1], ParagraphBoundary)
                ):
                    forced_paragraph_style_positions.add(target_pos - 1)
                    forced_newline_text_style_positions.add(target_pos - 1)
                target_pos += 1
                continue

            if isinstance(target_unit, SectionBreakUnit):
                section_type = target_unit.style.section_type
                if isinstance(section_type, UnsetType):
                    raise UnsupportedTransformation(
                        "cannot insert a section break with an unset section type"
                    )
                section_break_utf16_offset = (
                    target.utf16_index(target_pos) - target_range_start_utf16_index
                )
                edits.append(
                    InsertSectionBreak(
                        index=(insertion_utf16_index + section_break_utf16_offset),
                        section_type=cast(
                            Literal[
                                "SECTION_TYPE_UNSPECIFIED",
                                "CONTINUOUS",
                                "NEXT_PAGE",
                            ],
                            section_type,
                        ),
                        preceding_boundary=preceding_boundary,
                    )
                )
                target_pos += 1
                continue

            raise UnsupportedTransformation(
                f"cannot insert {type(target_unit).__name__} content"
            )

    # Formatting
    # ----------
    # At this point the content requests, when executed, leave the document with
    # the same widths and structure as the target stream. Formatting requests
    # can therefore use target UTF-16 indices. For equal opcode stream ranges,
    # compare the matched source formatting. Inserted and replaced units have no
    # source formatting that can be trusted, so their target formatting is reapplied.
    bullet_edits: list[Edit] = []
    style_edits: list[Edit] = []

    # The bullet and style passes are easier to follow when they can walk the
    # target directly, including page breaks and inline opaque units between
    # paragraph text and boundaries. This map records the source unit aligned
    # with each target position. Inserted and replaced target positions are absent.
    source_units_by_target_pos: dict[int, ContentUnit] = {}
    for (
        tag,
        source_start_pos,
        _source_end_pos,
        target_start_pos,
        target_end_pos,
    ) in opcodes:
        if tag == "equal":
            for range_offset in range(target_end_pos - target_start_pos):
                source_units_by_target_pos[target_start_pos + range_offset] = (
                    source.items[source_start_pos + range_offset]
                )

    # The content loop consumed these boundaries together with their structures,
    # so they have no equal source unit even though Google will create them.
    # Add a plain boundary placeholder so the formatting pass treats them as
    # present instead of emitting unnecessary resets for missing content.
    for target_pos in inserted_structural_boundary_positions:
        source_units_by_target_pos[target_pos] = ParagraphBoundary()

    # Bullet formatting
    # -----------------
    # Walk the target units in their document order. Text and equations are
    # inline paragraph content, so they do not interrupt a list. A paragraph
    # boundary either continues the current list run or starts a different kind
    # of paragraph. Any block-level unit ends the run naturally because it is
    # neither inline content nor a paragraph boundary.
    target_pos = 0
    while target_pos < len(target.items):
        target_unit = target.items[target_pos]
        if is_inline_paragraph_unit(target_unit):
            target_pos += 1
            continue
        if isinstance(target_unit, ParagraphBoundary):
            target_boundary_unit = target_unit
        else:
            target_pos += 1
            continue
        source_unit = source_units_by_target_pos.get(target_pos)
        source_boundary_unit = (
            source_unit if isinstance(source_unit, ParagraphBoundary) else None
        )
        source_bullet = (
            source_boundary_unit.bullet if source_boundary_unit is not None else UNSET
        )
        paragraph_start_utf16_index, paragraph_end_utf16_index = (
            target_paragraph_utf16_range_by_target_pos[target_pos]
        )

        # New bullet lists
        # ----------------
        # A BulletPreset asks Google to create a list. Keep walking through
        # inline content and matching paragraph boundaries until something else
        # ends the run, then create all of its paragraphs with one request.
        if isinstance(target_boundary_unit.bullet, BulletPreset):
            target_preset = target_boundary_unit.bullet
            preset_run_boundaries = [(target_pos, target_preset)]
            target_pos += 1
            # The current paragraph is already part of the run. Move through the
            # following paragraph's inline content until we reach its boundary.
            # A boundary with the same preset extends the run. Anything else is
            # left for the outer loop to handle on its next pass.
            while target_pos < len(target.items):
                candidate_unit = target.items[target_pos]
                if is_inline_paragraph_unit(candidate_unit):
                    target_pos += 1
                    continue
                if isinstance(candidate_unit, ParagraphBoundary):
                    candidate_preset = candidate_unit.bullet
                    if isinstance(candidate_preset, BulletPreset):
                        if candidate_preset.preset == target_preset.preset:
                            preset_run_boundaries.append((target_pos, candidate_preset))
                            target_pos += 1
                            continue
                break

            # We now know every paragraph that belongs to this new list. Remove
            # any old list membership paragraph by paragraph, while building the
            # range and nesting information needed for the replacement run.
            preset_run_paragraphs: list[BulletParagraph] = []
            for run_pos, run_preset in preset_run_boundaries:
                run_source_unit = source_units_by_target_pos.get(run_pos)
                run_source_boundary_unit = (
                    run_source_unit
                    if isinstance(run_source_unit, ParagraphBoundary)
                    else None
                )
                run_start_utf16_index, run_end_utf16_index = (
                    target_paragraph_utf16_range_by_target_pos[run_pos]
                )
                if (
                    run_source_boundary_unit is not None
                    and run_source_boundary_unit.bullet is not UNSET
                ):
                    bullet_edits.append(
                        DeleteParagraphBullets(
                            start_index=run_start_utf16_index,
                            end_index=run_end_utf16_index,
                        )
                    )
                preset_run_paragraphs.append(
                    BulletParagraph(
                        start_index=run_start_utf16_index,
                        end_index=run_end_utf16_index,
                        nesting_level=run_preset.nesting_level,
                    )
                )

            # Lowering needs the complete run in one edit so Google gives every
            # paragraph the same list ID while preserving their nesting levels.
            bullet_edits.append(
                ApplyBulletRun(
                    paragraphs=tuple(preset_run_paragraphs),
                    preset=target_preset.preset,
                )
            )
            continue

        # Existing bullet lists
        # ---------------------
        # A Bullet with a list ID refers to a list already present in the source
        # document. Consume the complete run so a nesting change can rebuild all
        # of its paragraphs together.
        if isinstance(target_boundary_unit.bullet, Bullet):
            target_bullet = target_boundary_unit.bullet
            existing_run_boundaries = [
                (target_pos, target_boundary_unit, target_bullet)
            ]
            target_pos += 1
            # As with a new list, walk through inline content to each following
            # paragraph boundary. The run continues only while those boundaries
            # carry the same Google-assigned list ID. We stop before consuming
            # the first different paragraph or block-level unit.
            while target_pos < len(target.items):
                candidate_unit = target.items[target_pos]
                if is_inline_paragraph_unit(candidate_unit):
                    target_pos += 1
                    continue
                if isinstance(candidate_unit, ParagraphBoundary):
                    candidate_bullet = candidate_unit.bullet
                    if isinstance(candidate_bullet, Bullet):
                        if candidate_bullet.list_id == target_bullet.list_id:
                            existing_run_boundaries.append(
                                (target_pos, candidate_unit, candidate_bullet)
                            )
                            target_pos += 1
                            continue
                break

            # Compare the complete target run with its aligned source
            # paragraphs. Google does not let us move a paragraph directly from
            # one existing list ID to another. A nesting change is possible, but
            # it means deleting and recreating this entire run. Remember one
            # changed pair so we can recover the list definition below.
            changed_boundary_units: (
                tuple[
                    ParagraphBoundary,
                    ParagraphBoundary,
                ]
                | None
            ) = None
            for run_pos, run_boundary_unit, run_bullet in existing_run_boundaries:
                run_source_unit = source_units_by_target_pos.get(run_pos)
                if isinstance(run_source_unit, ParagraphBoundary) and isinstance(
                    run_source_unit.bullet,
                    Bullet,
                ):
                    if run_bullet.list_id != run_source_unit.bullet.list_id:
                        raise UnsupportedTransformation(
                            "moving paragraphs between existing lists is not supported"
                        )
                    if (
                        changed_boundary_units is None
                        and run_bullet.nesting_level
                        != run_source_unit.bullet.nesting_level
                    ):
                        changed_boundary_units = (run_boundary_unit, run_source_unit)

            if changed_boundary_units is not None:
                changed_target_boundary_unit, changed_source_boundary_unit = (
                    changed_boundary_units
                )
                # createParagraphBullets accepts a preset rather than the source
                # list definition. Use the exact matching preset when possible;
                # otherwise the caller must explicitly allow us to normalize a
                # customized list to the closest preset.
                definition = (
                    changed_target_boundary_unit.list_definition
                    if isinstance(
                        changed_target_boundary_unit.list_definition,
                        ListDefinition,
                    )
                    else changed_source_boundary_unit.list_definition
                )
                if not isinstance(definition, ListDefinition):
                    raise UnsupportedTransformation(
                        "the existing bullet list definition is not loaded"
                    )
                preset = exact_preset(definition)
                if preset is None:
                    if not context.allow_bullet_normalization:
                        raise UnsupportedTransformation(
                            "editing a customized bullet list requires "
                            "bullet normalization"
                        )
                    preset = closest_preset(definition)

                # Rebuilding uses two edits: first remove list membership from
                # the complete run, then apply one preset with the target nesting
                # level recorded for every paragraph.
                existing_run_paragraphs = tuple(
                    BulletParagraph(
                        start_index=(
                            target_paragraph_utf16_range_by_target_pos[run_pos][0]
                        ),
                        end_index=(
                            target_paragraph_utf16_range_by_target_pos[run_pos][1]
                        ),
                        nesting_level=run_bullet.nesting_level,
                    )
                    for run_pos, _run_boundary, run_bullet in existing_run_boundaries
                )
                bullet_edits.append(
                    DeleteParagraphBullets(
                        start_index=existing_run_paragraphs[0].start_index,
                        end_index=existing_run_paragraphs[-1].end_index,
                    )
                )
                bullet_edits.append(
                    ApplyBulletRun(
                        paragraphs=existing_run_paragraphs,
                        preset=preset,
                    )
                )
            continue

        # If the target paragraph no longer belongs to a list, remove its source
        # bullet formatting without touching the text that may carry comments.
        if target_boundary_unit.bullet is UNSET and source_bullet is not UNSET:
            bullet_edits.append(
                DeleteParagraphBullets(
                    start_index=paragraph_start_utf16_index,
                    end_index=paragraph_end_utf16_index,
                )
            )
        target_pos += 1

    # Text and paragraph styles
    # -------------------------
    # Styles operate on individual units, so walk the target once and compare
    # each unit with its aligned source unit when one exists.
    for target_pos, target_unit in enumerate(target.items):
        source_unit = source_units_by_target_pos.get(target_pos)

        unit_start_utf16_index = target.utf16_index(target_pos)
        unit_end_utf16_index = target.utf16_index(target_pos + 1)

        match target_unit:
            # Section formatting
            # ------------------
            case SectionBreakUnit() as target_section_unit:
                source_section_unit = (
                    source_unit if isinstance(source_unit, SectionBreakUnit) else None
                )
                if (
                    source_section_unit is not None
                    and source_section_unit.style.section_type
                    != target_section_unit.style.section_type
                ):
                    raise UnsupportedTransformation(
                        "changing a retained section break type is not supported"
                    )
                target_writable_style = writable_section_style(
                    target_section_unit.style
                )
                if source_section_unit is not None:
                    source_writable_style = writable_section_style(
                        source_section_unit.style
                    )
                    if any(
                        source_value is not UNSET and target_value is UNSET
                        for source_value, target_value in zip(
                            source_writable_style,
                            target_writable_style,
                        )
                    ):
                        raise UnsupportedTransformation(
                            "clearing a concrete section style is not supported"
                        )
                else:
                    source_writable_style = (UNSET,) * len(target_writable_style)

                if source_writable_style != target_writable_style and any(
                    value is not UNSET for value in target_writable_style
                ):
                    style_edits.append(
                        ApplySectionStyle(
                            start_index=unit_start_utf16_index,
                            end_index=unit_end_utf16_index,
                            section_style=target_section_unit.style,
                        )
                    )

            # Opaque and container units
            # --------------------------
            case EquationUnit() | OpaqueUnit() | TableUnit():
                pass

            case PageBreakUnit() as target_page_break_unit:
                source_page_break_unit = (
                    source_unit if isinstance(source_unit, PageBreakUnit) else None
                )
                if (
                    source_page_break_unit is None
                    or source_page_break_unit.text_style
                    != target_page_break_unit.text_style
                ):
                    style_edits.append(
                        ApplyTextStyle(
                            start_index=unit_start_utf16_index,
                            end_index=unit_end_utf16_index,
                            text_style=target_page_break_unit.text_style,
                        )
                    )

            # Text styles
            # -----------
            case TextUnit() as target_text_unit:
                source_text_unit = (
                    source_unit if isinstance(source_unit, TextUnit) else None
                )
                if (
                    source_text_unit is None
                    or source_text_unit.text_style != target_text_unit.text_style
                ):
                    style_edits.append(
                        ApplyTextStyle(
                            start_index=unit_start_utf16_index,
                            end_index=unit_end_utf16_index,
                            text_style=target_text_unit.text_style,
                        )
                    )

            # Paragraph formatting
            # --------------------
            case ParagraphBoundary() as target_boundary_unit:
                # The boundary is the stream representation of a paragraph's
                # final newline. It carries newline text style, paragraph
                # style, and list membership. The remembered paragraph UTF-16
                # range locates the complete paragraph that ends here.
                (
                    paragraph_start_utf16_index,
                    paragraph_end_utf16_index,
                ) = target_paragraph_utf16_range_by_target_pos[target_pos]
                source_boundary_unit = (
                    source_unit if isinstance(source_unit, ParagraphBoundary) else None
                )
                # Paragraph and newline styles
                # ----------------------------
                # Bullet operations do not restore either the newline's text
                # style or the paragraph's own style. Compare and emit those
                # independently after deciding the list operation.
                if (
                    target_pos in forced_newline_text_style_positions
                    or source_boundary_unit is None
                    or source_boundary_unit.text_style
                    != target_boundary_unit.text_style
                ):
                    style_edits.append(
                        ApplyTextStyle(
                            start_index=unit_start_utf16_index,
                            end_index=unit_end_utf16_index,
                            text_style=target_boundary_unit.text_style,
                        )
                    )
                if (
                    target_pos in forced_paragraph_style_positions
                    or source_boundary_unit is None
                    or writable_paragraph_style(source_boundary_unit.paragraph_style)
                    != writable_paragraph_style(target_boundary_unit.paragraph_style)
                ):
                    style_edits.append(
                        ApplyParagraphStyle(
                            start_index=paragraph_start_utf16_index,
                            end_index=paragraph_end_utf16_index,
                            paragraph_style=target_boundary_unit.paragraph_style,
                            inside_table=context.inside_table,
                        )
                    )

            case _:
                raise NotImplementedError(type(target_unit).__name__)

    # Finalize the edit script
    # ------------------------
    edits.extend(bullet_edits)
    edits.extend(style_edits)

    # Character-level matching can produce one identical ApplyTextStyle action
    # per character. Merge adjacent actions with the same style so lowering emits
    # one request for the complete continuous UTF-16 range instead of many tiny ones.
    collapsed_edits: list[Edit] = []
    for edit in edits:
        previous_edit = collapsed_edits[-1] if collapsed_edits else None
        if (
            isinstance(previous_edit, ApplyTextStyle)
            and isinstance(edit, ApplyTextStyle)
            and previous_edit.end_index == edit.start_index
            and previous_edit.text_style == edit.text_style
        ):
            collapsed_edits[-1] = ApplyTextStyle(
                start_index=previous_edit.start_index,
                end_index=edit.end_index,
                text_style=edit.text_style,
            )
        else:
            collapsed_edits.append(edit)

    # Content edits use source-stream indices, while formatting uses target-stream
    # indices. Keep all formatting after the content has reached the target shape.
    # Text styles remain last because applying a named paragraph style can reset
    # inline formatting.
    formatting_types = (
        ApplyBulletRun,
        DeleteParagraphBullets,
        ApplyParagraphStyle,
        ApplySectionStyle,
        ApplyTableColumnProperties,
        ApplyTableRowStyle,
        ApplyTableCellStyle,
        ApplyTextStyle,
    )
    ordered_edits = [
        edit for edit in collapsed_edits if not isinstance(edit, formatting_types)
    ]
    ordered_edits.extend(
        edit
        for edit in collapsed_edits
        if isinstance(edit, formatting_types) and not isinstance(edit, ApplyTextStyle)
    )
    ordered_edits.extend(
        edit for edit in collapsed_edits if isinstance(edit, ApplyTextStyle)
    )
    return EditScript(edits=ordered_edits)
