from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from gdocs_patch.models import (
    UNSET,
    Bullet,
    Dimension,
    ListDefinition,
    ParagraphStyle,
    TableCellStyle,
    TableColumn,
    TextStyle,
    UnsetType,
)

from .bullets import closest_preset, exact_preset
from .content_stream import (
    BulletPreset,
    ContentStream,
    EquationUnit,
    ParagraphBoundary,
    TableCellUnit,
    TableUnit,
    TextUnit,
)


class UnsupportedTransformation(Exception):
    pass


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
class InsertTable(Edit):
    index: int
    rows: int
    columns: int


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


def match_content(*, source: ContentStream, target: ContentStream) -> Sequence[Opcode]:
    return SequenceMatcher(
        a=source.comparison_values(),
        b=target.comparison_values(),
        autojunk=False,
    ).get_opcodes()


def compile_inserted_table(*, table: TableUnit, index: int) -> list[Edit]:
    edits: list[Edit] = [
        InsertTable(
            index=index,
            rows=len(table.rows),
            columns=table.column_count,
        )
    ]
    cells = [
        (row_index, cell_index, cell)
        for row_index, row in enumerate(table.rows)
        for cell_index, cell in enumerate(row.cells)
    ]
    for row_index, cell_index, cell in reversed(cells):
        edits.extend(
            compile_content(
                source=ContentStream(items=[ParagraphBoundary()]),
                target=cell.content,
                start_index=index
                + table.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                ),
            )
        )

    if isinstance(table.column_properties, list):
        for column_index, column_properties in enumerate(table.column_properties):
            edits.append(
                ApplyTableColumnProperties(
                    table_start_index=index,
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
                    table_start_index=index,
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
                        table_start_index=index,
                        row_index=row_index,
                        column_index=sum(
                            previous_cell.column_span
                            for previous_cell in row.cells[:cell_index]
                        ),
                        row_span=cell.row_span,
                        column_span=cell.column_span,
                        cell_style=cell.style,
                    )
                )
    return edits


def compile_table(
    *,
    source: TableUnit,
    target: TableUnit,
    table_start_index: int,
    allow_bullet_normalization: bool,
) -> list[Edit]:
    available_source_rows = list(enumerate(source.rows))
    matched_rows: list[tuple[int, int]] = []
    new_row_indices: list[int] = []

    for target_row_index, target_row in enumerate(target.rows):
        source_row = next(
            (
                item
                for item in available_source_rows
                if item[1].row_key == target_row.row_key
            ),
            None,
        )
        if source_row is None:
            new_row_indices.append(target_row_index)
        else:
            available_source_rows.remove(source_row)
            matched_rows.append((source_row[0], target_row_index))

    edits: list[Edit] = []
    if len(target.rows) > len(source.rows):
        for row_index in new_row_indices:
            edits.append(
                InsertTableRow(
                    table_start_index=table_start_index,
                    row_index=max(0, row_index - 1),
                    column_index=0,
                    insert_below=row_index > 0,
                )
            )
    elif len(source.rows) > len(target.rows):
        for row_index, _row in reversed(available_source_rows):
            edits.append(
                DeleteTableRow(
                    table_start_index=table_start_index,
                    row_index=row_index,
                    column_index=0,
                )
            )

    matched_cells: list[tuple[int, int, TableCellUnit, TableCellUnit]] = []
    new_cells: list[tuple[int, int, TableCellUnit]] = []
    deleted_cell_indices: dict[int, list[int]] = {}
    source_rows_by_target = {
        target_row_index: source.rows[source_row_index]
        for source_row_index, target_row_index in matched_rows
    }

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

    column_delta = target.column_count - source.column_count
    if column_delta > 0:
        for column_index in [
            cell_index for row_index, cell_index, _cell in new_cells if row_index == 0
        ]:
            edits.append(
                InsertTableColumn(
                    table_start_index=table_start_index,
                    row_index=0,
                    column_index=max(0, column_index - 1),
                    insert_right=column_index > 0,
                )
            )
    elif column_delta < 0:
        for column_index in reversed(deleted_cell_indices.get(0, [])):
            edits.append(
                DeleteTableColumn(
                    table_start_index=table_start_index,
                    row_index=0,
                    column_index=column_index,
                )
            )

    merged_target_cell_ids: set[int] = set()
    for row_index, cell_index, source_cell, target_cell in matched_cells:
        if (
            target_cell.row_span > source_cell.row_span
            or target_cell.column_span > source_cell.column_span
        ):
            edits.append(
                MergeTableCells(
                    table_start_index=table_start_index,
                    row_index=row_index,
                    column_index=cell_index,
                    row_span=target_cell.row_span,
                    column_span=target_cell.column_span,
                )
            )
            merged_target_cell_ids.add(id(target_cell))
        elif (
            source_cell.row_span > target_cell.row_span
            or source_cell.column_span > target_cell.column_span
        ):
            edits.append(
                UnmergeTableCells(
                    table_start_index=table_start_index,
                    row_index=row_index,
                    column_index=cell_index,
                    row_span=source_cell.row_span,
                    column_span=source_cell.column_span,
                )
            )

    for row_index, cell_index, cell in reversed(new_cells):
        edits.extend(
            compile_content(
                source=ContentStream(items=[ParagraphBoundary()]),
                target=cell.content,
                start_index=table_start_index
                + target.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                ),
            )
        )

    for row_index, cell_index, source_cell, target_cell in reversed(matched_cells):
        if id(target_cell) in merged_target_cell_ids:
            continue
        edits.extend(
            generate_edit_script(
                source=source_cell.content,
                target=target_cell.content,
                start_index=table_start_index
                + target.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                ),
                allow_bullet_normalization=allow_bullet_normalization,
            ).edits
        )

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
                        table_start_index=table_start_index,
                        column_index=column_index,
                        column_properties=target_properties,
                    )
                )

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
                    table_start_index=table_start_index,
                    row_index=target_row_index,
                    min_height=target_row.min_height,
                    prevent_overflow=target_row.prevent_overflow,
                    is_header=target_row.is_header,
                )
            )

    source_cells_by_target = {
        (row_index, cell_index): source_cell
        for row_index, cell_index, source_cell, _target_cell in matched_cells
    }
    for row_index, row in enumerate(target.rows):
        for cell_index, target_cell in enumerate(row.cells):
            source_cell = source_cells_by_target.get((row_index, cell_index))
            source_style = source_cell.style if source_cell is not None else UNSET
            if writable_table_cell_style(source_style) != writable_table_cell_style(
                target_cell.style
            ):
                edits.append(
                    ApplyTableCellStyle(
                        table_start_index=table_start_index,
                        row_index=row_index,
                        column_index=sum(
                            previous_cell.column_span
                            for previous_cell in row.cells[:cell_index]
                        ),
                        row_span=target_cell.row_span,
                        column_span=target_cell.column_span,
                        cell_style=target_cell.style,
                    )
                )

    return edits


def generate_text_edits(
    *,
    source: ContentStream,
    target: ContentStream,
    opcode: Opcode,
    start_index: int,
) -> list[Edit]:
    tag, source_start, source_end, target_start, target_end = opcode
    index = source.utf16_index(source_start, start_index=start_index)
    edits: list[Edit] = []

    # A replacement deletes first so its insertion can reuse the same index.
    if tag in {"delete", "replace"}:
        edits.append(
            DeleteContent(
                start_index=index,
                end_index=source.utf16_index(source_end, start_index=start_index),
            )
        )
    if tag in {"insert", "replace"}:
        text = "".join(
            item.content if isinstance(item, TextUnit) else "\n"
            for item in target.items[target_start:target_end]
        )
        edits.append(InsertText(index=index, text=text))
    return edits


def compile_content(
    *, source: ContentStream, target: ContentStream, start_index: int
) -> list[Edit]:
    opcodes = match_content(source=source, target=target)
    edits: list[Edit] = []
    for opcode in reversed(opcodes):
        edits.extend(
            generate_text_edits(
                source=source,
                target=target,
                opcode=opcode,
                start_index=start_index,
            )
        )
    return edits


def generate_edit_script(
    *,
    source: ContentStream,
    target: ContentStream,
    start_index: int = 0,
    allow_bullet_normalization: bool = False,
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
    target_paragraph_utf16_ranges: dict[int, tuple[int, int]] = {}
    paragraph_start_utf16_index = start_index
    target_utf16_index = start_index
    for target_pos, target_unit in enumerate(target.items):
        target_utf16_index += target_unit.utf16_width
        if isinstance(target_unit, ParagraphBoundary):
            target_paragraph_utf16_ranges[target_pos] = (
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
        if tag in {"insert", "replace"} and any(
            isinstance(target_unit, EquationUnit)
            for target_unit in target.items[target_start_pos:target_end_pos]
        ):
            raise UnsupportedTransformation(
                "Google Docs cannot insert Equation elements"
            )

    # Deleting a paragraph boundary joins the surrounding text into one
    # paragraph. Google keeps one side's paragraph style during that merge, and
    # it may not be the target style. Remember the surviving target paragraph so
    # its style is reapplied even if SequenceMatcher considered it unchanged.

    # These are stream positions of target ParagraphBoundary units whose
    # paragraph styles must be reapplied after a source boundary is deleted.
    forced_paragraph_style_positions: set[int] = set()
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
    # Tables are outer stream units with their own nested compiler, so the code
    # below handles them separately from text.
    handled_table_target_positions: set[int] = set()
    for opcode in reversed(opcodes):
        tag, source_start_pos, source_end_pos, target_start_pos, target_end_pos = opcode

        # Existing tables
        # ---------------
        # Equal table units have the same retained table key. Their outer
        # structure remains in place, but rows, columns, cells, and cell content
        # may still differ, so recurse into each matched table.
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
                        compile_table(
                            source=source_unit,
                            target=target_unit,
                            table_start_index=source.utf16_index(
                                source_pos,
                                start_index=start_index,
                            ),
                            allow_bullet_normalization=allow_bullet_normalization,
                        )
                    )
                    handled_table_target_positions.add(target_pos)
            continue

        # New tables
        # ----------
        # A table in an inserted or replaced target stream range is new; existing
        # tables were handled above. InsertText cannot create it, so remove the
        # replaced source stream range and compile each new table separately.
        inserted_tables = [
            (target_pos, target_unit)
            for target_pos, target_unit in enumerate(
                target.items[target_start_pos:target_end_pos],
                start=target_start_pos,
            )
            if isinstance(target_unit, TableUnit)
        ]
        if inserted_tables:
            if tag == "replace":
                edits.append(
                    DeleteContent(
                        start_index=source.utf16_index(
                            source_start_pos,
                            start_index=start_index,
                        ),
                        end_index=source.utf16_index(
                            source_end_pos,
                            start_index=start_index,
                        ),
                    )
                )
            insertion_utf16_index = source.utf16_index(
                source_start_pos,
                start_index=start_index,
            )
            target_range_start_utf16_index = target.utf16_index(target_start_pos)
            for target_pos, table in inserted_tables:
                table_utf16_offset = (
                    target.utf16_index(target_pos) - target_range_start_utf16_index
                )
                table_insertion_utf16_index = insertion_utf16_index + table_utf16_offset
                edits.extend(
                    compile_inserted_table(
                        table=table,
                        index=table_insertion_utf16_index,
                    )
                )
                handled_table_target_positions.add(target_pos)
            continue

        # Text content
        # ------------
        edits.extend(
            generate_text_edits(
                source=source,
                target=target,
                opcode=opcode,
                start_index=start_index,
            )
        )

    # At this point the content requests, when executed, leave the document with
    # the same widths and structure as the target stream. Formatting requests
    # can therefore use target UTF-16 indices. For equal opcode stream ranges,
    # compare the matched source formatting. Inserted and replaced units have no
    # source formatting that can be trusted, so their target formatting is reapplied.
    bullet_edits: list[Edit] = []
    style_edits: list[Edit] = []
    # SequenceMatcher sees each paragraph boundary independently, whereas the
    # Docs API often has to recreate an entire list to change one unit's level.
    # Keep the ordered boundary stream positions so any changed unit can recover
    # its surrounding run. Once a run is emitted, mark all of its positions to
    # avoid emitting the same reconstruction again at the next paragraph.
    handled_bullet_target_positions: set[int] = set()
    target_boundary_positions = list(target_paragraph_utf16_ranges)
    for (
        tag,
        source_start_pos,
        _source_end_pos,
        target_start_pos,
        target_end_pos,
    ) in opcodes:
        for target_pos in range(target_start_pos, target_end_pos):
            if target_pos in handled_table_target_positions:
                continue
            target_unit = target.items[target_pos]
            # Equal stream ranges provide a corresponding source unit whose
            # formatting can be compared. Inserted and replaced target units have
            # no source unit and will receive their target formatting.
            source_unit = None
            if tag == "equal":
                source_unit = source.items[
                    source_start_pos + target_pos - target_start_pos
                ]

            unit_start_utf16_index = target.utf16_index(
                target_pos,
                start_index=start_index,
            )
            unit_end_utf16_index = target.utf16_index(
                target_pos + 1,
                start_index=start_index,
            )

            match target_unit:
                case EquationUnit() | TableUnit():
                    pass

                case TextUnit() as target_text:
                    source_text = (
                        source_unit if isinstance(source_unit, TextUnit) else None
                    )
                    if (
                        source_text is None
                        or source_text.text_style != target_text.text_style
                    ):
                        style_edits.append(
                            ApplyTextStyle(
                                start_index=unit_start_utf16_index,
                                end_index=unit_end_utf16_index,
                                text_style=target_text.text_style,
                            )
                        )

                case ParagraphBoundary() as target_boundary:
                    # The boundary is the stream representation of a paragraph's
                    # final newline. It carries newline text style, paragraph
                    # style, and list membership. The remembered paragraph UTF-16
                    # range locates the complete paragraph that ends here.
                    (
                        paragraph_start_utf16_index,
                        paragraph_end_utf16_index,
                    ) = target_paragraph_utf16_ranges[target_pos]
                    source_boundary = (
                        source_unit
                        if isinstance(source_unit, ParagraphBoundary)
                        else None
                    )
                    source_bullet = (
                        source_boundary.bullet if source_boundary is not None else UNSET
                    )

                    # BulletPreset means the target is asking Google to create a
                    # list rather than preserve one returned by documents.get.
                    # If this paragraph currently belongs to a list, remove that
                    # membership before applying the requested preset.
                    if isinstance(target_boundary.bullet, BulletPreset):
                        if source_bullet is not UNSET:
                            bullet_edits.append(
                                DeleteParagraphBullets(
                                    start_index=paragraph_start_utf16_index,
                                    end_index=paragraph_end_utf16_index,
                                )
                            )
                        bullet_paragraph = BulletParagraph(
                            start_index=paragraph_start_utf16_index,
                            end_index=paragraph_end_utf16_index,
                            nesting_level=target_boundary.bullet.nesting_level,
                        )
                        # Lowering creates nesting by temporarily inserting tabs
                        # before each paragraph and then sending one
                        # createParagraphBullets request. Adjacent paragraphs with
                        # the same preset must therefore be accumulated into one
                        # ApplyBulletRun; separate requests do not reliably retain
                        # their mixed nesting levels.
                        previous_bullet_edit = (
                            bullet_edits[-1] if bullet_edits else None
                        )
                        if (
                            isinstance(previous_bullet_edit, ApplyBulletRun)
                            and previous_bullet_edit.preset
                            == target_boundary.bullet.preset
                            and previous_bullet_edit.paragraphs[-1].end_index
                            == paragraph_start_utf16_index
                        ):
                            bullet_edits[-1] = ApplyBulletRun(
                                paragraphs=(
                                    *previous_bullet_edit.paragraphs,
                                    bullet_paragraph,
                                ),
                                preset=target_boundary.bullet.preset,
                            )
                        else:
                            bullet_edits.append(
                                ApplyBulletRun(
                                    paragraphs=(bullet_paragraph,),
                                    preset=target_boundary.bullet.preset,
                                )
                            )
                    # Bullet contains a Google-assigned list ID, which means the
                    # target intends to preserve an existing list. No request is
                    # needed while both the ID and nesting level are unchanged.
                    # Moving a paragraph to another existing list cannot be
                    # expressed by the API, and changing a nesting level requires
                    # deleting and recreating the complete contiguous list run.
                    elif isinstance(target_boundary.bullet, Bullet):
                        if (
                            target_pos not in handled_bullet_target_positions
                            and isinstance(source_bullet, Bullet)
                            and (
                                target_boundary.bullet.list_id != source_bullet.list_id
                                or target_boundary.bullet.nesting_level
                                != source_bullet.nesting_level
                            )
                        ):
                            if target_boundary.bullet.list_id != source_bullet.list_id:
                                raise UnsupportedTransformation(
                                    "moving paragraphs between existing lists is not supported"
                                )
                            # createParagraphBullets accepts one of Google's
                            # fixed presets; it cannot accept the ListDefinition
                            # returned by documents.get. If that definition is an
                            # exact preset, rebuilding preserves its appearance.
                            # Otherwise rebuilding normalizes a customized list,
                            # which is only allowed when the caller opts into it.
                            definition = (
                                target_boundary.list_definition
                                if isinstance(
                                    target_boundary.list_definition,
                                    ListDefinition,
                                )
                                else (
                                    source_boundary.list_definition
                                    if source_boundary is not None
                                    else UNSET
                                )
                            )
                            if not isinstance(definition, ListDefinition):
                                raise UnsupportedTransformation(
                                    "the existing bullet list definition is not loaded"
                                )
                            preset = exact_preset(definition)
                            if preset is None:
                                if not allow_bullet_normalization:
                                    raise UnsupportedTransformation(
                                        "editing a customized bullet list requires "
                                        "bullet normalization"
                                    )
                                preset = closest_preset(definition)

                            # The current boundary may be in the middle of its
                            # list. Walk paragraph boundaries in both directions
                            # to recover the whole contiguous run with this list
                            # ID. A table between two boundaries breaks the run:
                            # paragraphs on opposite sides cannot be recreated by
                            # one paragraph-range request.
                            run_boundary_list_pos = target_boundary_positions.index(
                                target_pos
                            )
                            first_boundary_list_pos = run_boundary_list_pos
                            while first_boundary_list_pos > 0:
                                candidate_pos = target_boundary_positions[
                                    first_boundary_list_pos - 1
                                ]
                                candidate = target.items[candidate_pos]
                                if (
                                    not isinstance(candidate, ParagraphBoundary)
                                    or not isinstance(candidate.bullet, Bullet)
                                    or candidate.bullet.list_id
                                    != target_boundary.bullet.list_id
                                    or any(
                                        isinstance(intervening_unit, TableUnit)
                                        for intervening_unit in target.items[
                                            candidate_pos
                                            + 1 : target_boundary_positions[
                                                first_boundary_list_pos
                                            ]
                                        ]
                                    )
                                ):
                                    break
                                first_boundary_list_pos -= 1

                            last_boundary_list_pos = run_boundary_list_pos
                            while last_boundary_list_pos + 1 < len(
                                target_boundary_positions
                            ):
                                candidate_pos = target_boundary_positions[
                                    last_boundary_list_pos + 1
                                ]
                                candidate = target.items[candidate_pos]
                                if (
                                    not isinstance(candidate, ParagraphBoundary)
                                    or not isinstance(candidate.bullet, Bullet)
                                    or candidate.bullet.list_id
                                    != target_boundary.bullet.list_id
                                    or any(
                                        isinstance(intervening_unit, TableUnit)
                                        for intervening_unit in target.items[
                                            target_boundary_positions[
                                                last_boundary_list_pos
                                            ]
                                            + 1 : candidate_pos
                                        ]
                                    )
                                ):
                                    break
                                last_boundary_list_pos += 1

                            # The scan above found stream positions. Convert each
                            # one into the paragraph UTF-16 range and desired nesting
                            # level that lowering needs to delete and recreate the
                            # run after all content edits have completed.
                            run_positions = target_boundary_positions[
                                first_boundary_list_pos : last_boundary_list_pos + 1
                            ]
                            run_paragraph_list: list[BulletParagraph] = []
                            for run_pos in run_positions:
                                run_boundary = target.items[run_pos]
                                if isinstance(
                                    run_boundary, ParagraphBoundary
                                ) and isinstance(run_boundary.bullet, Bullet):
                                    run_paragraph_list.append(
                                        BulletParagraph(
                                            start_index=target_paragraph_utf16_ranges[
                                                run_pos
                                            ][0],
                                            end_index=target_paragraph_utf16_ranges[
                                                run_pos
                                            ][1],
                                            nesting_level=run_boundary.bullet.nesting_level,
                                        )
                                    )
                            run_paragraphs = tuple(run_paragraph_list)
                            bullet_edits.append(
                                DeleteParagraphBullets(
                                    start_index=run_paragraphs[0].start_index,
                                    end_index=run_paragraphs[-1].end_index,
                                )
                            )
                            bullet_edits.append(
                                ApplyBulletRun(
                                    paragraphs=run_paragraphs,
                                    preset=preset,
                                )
                            )
                            # The outer loop will eventually visit every boundary
                            # in this run. Record them all now so those later visits
                            # do not emit duplicate delete-and-recreate actions.
                            handled_bullet_target_positions.update(run_positions)
                    # When the target paragraph is no longer bulleted, remove
                    # only its bullet formatting. The text is left in place so
                    # comments and other text-bound metadata survive.
                    elif target_boundary.bullet is UNSET and source_bullet is not UNSET:
                        bullet_edits.append(
                            DeleteParagraphBullets(
                                start_index=paragraph_start_utf16_index,
                                end_index=paragraph_end_utf16_index,
                            )
                        )

                    # Bullet operations do not restore either the newline's text
                    # style or the paragraph's own style. Compare and emit those
                    # independently after deciding the list operation.
                    if (
                        source_boundary is None
                        or source_boundary.text_style != target_boundary.text_style
                    ):
                        style_edits.append(
                            ApplyTextStyle(
                                start_index=unit_start_utf16_index,
                                end_index=unit_end_utf16_index,
                                text_style=target_boundary.text_style,
                            )
                        )
                    if (
                        target_pos in forced_paragraph_style_positions
                        or source_boundary is None
                        or writable_paragraph_style(source_boundary.paragraph_style)
                        != writable_paragraph_style(target_boundary.paragraph_style)
                    ):
                        style_edits.append(
                            ApplyParagraphStyle(
                                start_index=paragraph_start_utf16_index,
                                end_index=paragraph_end_utf16_index,
                                paragraph_style=target_boundary.paragraph_style,
                            )
                        )

                case _:
                    raise NotImplementedError(type(target_unit).__name__)

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

    # Google may reset inline text formatting when a named paragraph style is
    # applied. Keep text-style actions last so they restore the target's inline
    # formatting after every paragraph-level request has finished.
    ordered_edits = [
        edit for edit in collapsed_edits if not isinstance(edit, ApplyTextStyle)
    ]
    ordered_edits.extend(
        edit for edit in collapsed_edits if isinstance(edit, ApplyTextStyle)
    )
    return EditScript(edits=ordered_edits)
