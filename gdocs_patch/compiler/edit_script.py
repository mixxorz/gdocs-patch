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
    ContentUnit,
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


def compile_inserted_table(
    *,
    table: TableUnit,
    index: int,
    allow_bullet_normalization: bool,
) -> list[Edit]:
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
            generate_edit_script(
                source=ContentStream(items=[ParagraphBoundary()]),
                target=cell.content,
                start_index=index
                + table.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                ),
                allow_bullet_normalization=allow_bullet_normalization,
            ).edits
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
            generate_edit_script(
                source=ContentStream(items=[ParagraphBoundary()]),
                target=cell.content,
                start_index=table_start_index
                + target.cell_content_offset(
                    row_index=row_index,
                    cell_index=cell_index,
                ),
                allow_bullet_normalization=allow_bullet_normalization,
            ).edits
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


def is_insert_text_unit(unit: ContentUnit) -> bool:
    return isinstance(unit, (TextUnit, ParagraphBoundary))


def is_inline_paragraph_unit(unit: ContentUnit) -> bool:
    return isinstance(unit, (TextUnit, EquationUnit))


def generate_insert_text(
    *,
    target: ContentStream,
    target_start_pos: int,
    target_end_pos: int,
    insertion_utf16_index: int,
) -> InsertText:
    text = "".join(
        target_unit.content if isinstance(target_unit, TextUnit) else "\n"
        for target_unit in target.items[target_start_pos:target_end_pos]
    )
    return InsertText(index=insertion_utf16_index, text=text)


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
    target_paragraph_utf16_range_by_target_pos: dict[int, tuple[int, int]] = {}
    paragraph_start_utf16_index = start_index
    target_utf16_index = start_index
    for target_pos, target_unit in enumerate(target.items):
        target_utf16_index += target_unit.utf16_width
        if isinstance(target_unit, ParagraphBoundary):
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
    # The loop below inspects the units covered by each opcode. Most equal units
    # need no content edit. Tables are the exception because their outer unit can
    # match while rows, cells, or cell content still need to change.
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
            continue

        # Changed content
        # ---------------
        # Insert, delete, and replace opcodes do not align their source and
        # target units. Delete the complete source range once, then walk the
        # target range and create whatever units it contains.
        insertion_utf16_index = source.utf16_index(
            source_start_pos,
            start_index=start_index,
        )
        if tag in {"delete", "replace"}:
            edits.append(
                DeleteContent(
                    start_index=insertion_utf16_index,
                    end_index=source.utf16_index(
                        source_end_pos,
                        start_index=start_index,
                    ),
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
                edits.append(
                    generate_insert_text(
                        target=target,
                        target_start_pos=text_start_pos,
                        target_end_pos=target_pos,
                        insertion_utf16_index=(
                            insertion_utf16_index + text_utf16_offset
                        ),
                    )
                )
                continue

            if isinstance(target_unit, TableUnit):
                table_utf16_offset = (
                    target.utf16_index(target_pos) - target_range_start_utf16_index
                )
                edits.extend(
                    compile_inserted_table(
                        table=target_unit,
                        index=insertion_utf16_index + table_utf16_offset,
                        allow_bullet_normalization=allow_bullet_normalization,
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
    # target directly. This map records the source unit aligned with each target
    # position. Inserted and replaced target positions are absent from the map.
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
                    if not allow_bullet_normalization:
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

        unit_start_utf16_index = target.utf16_index(
            target_pos,
            start_index=start_index,
        )
        unit_end_utf16_index = target.utf16_index(
            target_pos + 1,
            start_index=start_index,
        )

        match target_unit:
            # Opaque and container units
            # --------------------------
            case EquationUnit() | TableUnit():
                pass

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
                    source_boundary_unit is None
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
