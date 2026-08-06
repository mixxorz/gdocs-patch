from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from gdocs_patch.models import UNSET, ParagraphStyle, TextStyle, UnsetType

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


def first_different_index(*, source: Sequence[object], target: Sequence[object]) -> int:
    for index, (source_item, target_item) in enumerate(
        zip(source, target, strict=False)
    ):
        if source_item != target_item:
            return index
    return min(len(source), len(target))


def compile_inserted_table(*, table: TableUnit, index: int) -> list[Edit]:
    edits: list[Edit] = [
        InsertTable(
            index=index,
            rows=len(table.rows),
            columns=table.column_count,
        )
    ]
    for row_index, row in enumerate(table.rows):
        for cell_index, cell in enumerate(row.cells):
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
    return edits


def compile_table(
    *,
    source: TableUnit,
    target: TableUnit,
    table_start_index: int,
) -> list[Edit]:
    changed_row = first_different_index(
        source=[row.row_key for row in source.rows],
        target=[row.row_key for row in target.rows],
    )
    added_rows = len(target.rows) - len(source.rows)
    edits: list[Edit] = []

    for offset in range(max(0, added_rows)):
        new_row = changed_row + offset
        edits.append(
            InsertTableRow(
                table_start_index=table_start_index,
                row_index=max(0, new_row - 1),
                column_index=0,
                insert_below=new_row > 0,
            )
        )

    for row_index in range(changed_row, changed_row + max(0, added_rows)):
        for cell_index, cell in enumerate(target.rows[row_index].cells):
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

    for target_row_index in reversed(range(len(target.rows))):
        if changed_row <= target_row_index < changed_row + max(0, added_rows):
            continue
        source_row_index = target_row_index
        if target_row_index >= changed_row + max(0, added_rows):
            source_row_index -= max(0, added_rows)
        if source_row_index >= len(source.rows):
            continue
        target_row = target.rows[target_row_index]
        available_source_cells = list(source.rows[source_row_index].cells)
        matched_cells: list[tuple[int, TableCellUnit, TableCellUnit]] = []
        for cell_index, target_cell in enumerate(target_row.cells):
            source_cell = next(
                (
                    cell
                    for cell in available_source_cells
                    if cell.cell_key == target_cell.cell_key
                ),
                None,
            )
            if source_cell is not None:
                available_source_cells.remove(source_cell)
                matched_cells.append((cell_index, source_cell, target_cell))

        for cell_index, source_cell, target_cell in reversed(matched_cells):
            edits.extend(
                generate_edit_script(
                    source=source_cell.content,
                    target=target_cell.content,
                    start_index=table_start_index
                    + target.cell_content_offset(
                        row_index=target_row_index,
                        cell_index=cell_index,
                    ),
                ).edits
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
                        or source_boundary.paragraph_style
                        != target_boundary.paragraph_style
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
