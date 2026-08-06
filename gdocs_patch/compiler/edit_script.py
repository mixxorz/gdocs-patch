from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

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
class CreateParagraphBullets(Edit):
    start_index: int
    end_index: int
    bullet_preset: BulletPreset


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
    *, source: ContentStream, target: ContentStream, start_index: int = 0
) -> EditScript:
    """Describe how to change source content and styles into the target."""

    # A paragraph ends at its boundary. Save its complete target range so a
    # boundary style change can style the paragraph rather than only its newline.
    target_paragraph_ranges: dict[int, tuple[int, int]] = {}
    paragraph_start = start_index
    target_index = start_index
    for position, item in enumerate(target.items):
        target_index += item.utf16_width
        if isinstance(item, ParagraphBoundary):
            target_paragraph_ranges[position] = (paragraph_start, target_index)
            paragraph_start = target_index

    edits: list[Edit] = []
    opcodes = match_content(source=source, target=target)

    for tag, _source_start, _source_end, target_start, target_end in opcodes:
        if tag in {"insert", "replace"} and any(
            isinstance(item, EquationUnit)
            for item in target.items[target_start:target_end]
        ):
            raise UnsupportedTransformation(
                "Google Docs cannot insert Equation elements"
            )

    # Deleting a paragraph boundary can change the merged paragraph's style.
    # Find the target boundary ending that paragraph so its style is reapplied.
    forced_paragraph_style_positions: set[int] = set()
    for tag, source_start, source_end, target_start, _target_end in opcodes:
        if tag not in {"delete", "replace"} or not any(
            isinstance(item, ParagraphBoundary)
            for item in source.items[source_start:source_end]
        ):
            continue
        for target_position in range(target_start, len(target.items)):
            if isinstance(target.items[target_position], ParagraphBoundary):
                forced_paragraph_style_positions.add(target_position)
                break

    # Apply content changes from right to left. Changes at later indices cannot
    # shift the source indices used by earlier changes.
    handled_table_target_positions: set[int] = set()
    for opcode in reversed(opcodes):
        tag, source_start, source_end, target_start, target_end = opcode

        if tag == "equal":
            for target_position in range(target_start, target_end):
                target_item = target.items[target_position]
                source_item = source.items[
                    source_start + target_position - target_start
                ]
                if isinstance(source_item, TableUnit) and isinstance(
                    target_item, TableUnit
                ):
                    edits.extend(
                        compile_table(
                            source=source_item,
                            target=target_item,
                            table_start_index=source.utf16_index(
                                source_start + target_position - target_start,
                                start_index=start_index,
                            ),
                        )
                    )
                    handled_table_target_positions.add(target_position)
            continue

        inserted_tables = [
            (target_position, item)
            for target_position, item in enumerate(
                target.items[target_start:target_end],
                start=target_start,
            )
            if isinstance(item, TableUnit)
        ]
        if inserted_tables:
            if tag == "replace":
                edits.append(
                    DeleteContent(
                        start_index=source.utf16_index(
                            source_start,
                            start_index=start_index,
                        ),
                        end_index=source.utf16_index(
                            source_end,
                            start_index=start_index,
                        ),
                    )
                )
            insertion_index = source.utf16_index(
                source_start,
                start_index=start_index,
            )
            target_slice_index = target.utf16_index(target_start)
            for target_position, table in inserted_tables:
                edits.extend(
                    compile_inserted_table(
                        table=table,
                        index=insertion_index
                        + target.utf16_index(target_position)
                        - target_slice_index,
                    )
                )
                handled_table_target_positions.add(target_position)
            continue

        edits.extend(
            generate_text_edits(
                source=source,
                target=target,
                opcode=opcode,
                start_index=start_index,
            )
        )

    # Content edits leave the document with the target shape, so style edits can
    # now use target indices. Equal opcodes provide a source style to compare;
    # inserted and replaced target items have no dependable inherited style.
    for tag, source_start, _source_end, target_start, target_end in opcodes:
        for target_position in range(target_start, target_end):
            if target_position in handled_table_target_positions:
                continue
            target_item = target.items[target_position]
            source_item = None
            if tag == "equal":
                source_item = source.items[
                    source_start + target_position - target_start
                ]

            item_start_index = target.utf16_index(
                target_position,
                start_index=start_index,
            )
            item_end_index = target.utf16_index(
                target_position + 1,
                start_index=start_index,
            )

            match target_item:
                case EquationUnit() | TableUnit():
                    pass

                case TextUnit() as target_text:
                    source_text = (
                        source_item if isinstance(source_item, TextUnit) else None
                    )
                    if (
                        source_text is None
                        or source_text.text_style != target_text.text_style
                    ):
                        edits.append(
                            ApplyTextStyle(
                                start_index=item_start_index,
                                end_index=item_end_index,
                                text_style=target_text.text_style,
                            )
                        )

                case ParagraphBoundary() as target_boundary:
                    # A boundary carries its list membership and the styles of
                    # both its newline and the paragraph ending there.
                    paragraph_start, paragraph_end = target_paragraph_ranges[
                        target_position
                    ]
                    source_boundary = (
                        source_item
                        if isinstance(source_item, ParagraphBoundary)
                        else None
                    )
                    source_bullet = (
                        source_boundary.bullet if source_boundary is not None else UNSET
                    )

                    if isinstance(target_boundary.bullet, BulletPreset):
                        if source_bullet is not UNSET:
                            edits.append(
                                DeleteParagraphBullets(
                                    start_index=paragraph_start,
                                    end_index=paragraph_end,
                                )
                            )
                        edits.append(
                            CreateParagraphBullets(
                                start_index=paragraph_start,
                                end_index=paragraph_end,
                                bullet_preset=target_boundary.bullet,
                            )
                        )
                    elif isinstance(target_boundary.bullet, Bullet):
                        if (
                            source_boundary is not None
                            and target_boundary.bullet != source_boundary.bullet
                        ):
                            raise UnsupportedTransformation(
                                "changing existing Google-assigned bullets is not supported"
                            )
                    elif target_boundary.bullet is UNSET and source_bullet is not UNSET:
                        edits.append(
                            DeleteParagraphBullets(
                                start_index=paragraph_start,
                                end_index=paragraph_end,
                            )
                        )

                    if (
                        source_boundary is None
                        or source_boundary.text_style != target_boundary.text_style
                    ):
                        edits.append(
                            ApplyTextStyle(
                                start_index=item_start_index,
                                end_index=item_end_index,
                                text_style=target_boundary.text_style,
                            )
                        )
                    if (
                        target_position in forced_paragraph_style_positions
                        or source_boundary is None
                        or writable_paragraph_style(source_boundary.paragraph_style)
                        != writable_paragraph_style(target_boundary.paragraph_style)
                    ):
                        edits.append(
                            ApplyParagraphStyle(
                                start_index=paragraph_start,
                                end_index=paragraph_end,
                                paragraph_style=target_boundary.paragraph_style,
                            )
                        )

                case _:
                    raise NotImplementedError(type(target_item).__name__)

    # Matching works one stream unit at a time. Merge adjacent text-style edits
    # so lowering can produce one Docs request for each continuous style range.
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

    return EditScript(edits=collapsed_edits)
