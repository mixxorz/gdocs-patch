from dataclasses import dataclass
from difflib import SequenceMatcher

from gdocs_patch.models import ParagraphStyle, TextStyle, UnsetType

from .content_stream import ContentStream, ParagraphBoundary, TextUnit


class Edit:
    """Marker type for operations in an edit script."""


@dataclass(frozen=True, kw_only=True)
class InsertText(Edit):
    index: int
    text: str


@dataclass(frozen=True, kw_only=True)
class DeleteContent(Edit):
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


def generate_edit_script(*, source: ContentStream, target: ContentStream) -> EditScript:
    """Describe how to change source content and styles into the target."""

    # Match only visible content and paragraph boundaries. Style differences do
    # not justify deleting text that can remain in place.
    source_values = [
        ("text", item.content)
        if isinstance(item, TextUnit)
        else ("paragraph_boundary", "")
        for item in source.items
    ]
    target_values = [
        ("text", item.content)
        if isinstance(item, TextUnit)
        else ("paragraph_boundary", "")
        for item in target.items
    ]

    # SequenceMatcher reports Python list positions. These maps translate every
    # position between stream items into the UTF-16 indices required by Docs.
    source_utf16_offset_map = [0]
    for item in source.items:
        source_utf16_offset_map.append(source_utf16_offset_map[-1] + item.utf16_width)

    target_utf16_offset_map = [0]

    # A paragraph ends at its boundary. Save its complete target range so a
    # boundary style change can style the paragraph rather than only its newline.
    target_paragraph_ranges: dict[int, tuple[int, int]] = {}
    paragraph_start = 0
    for position, item in enumerate(target.items):
        target_utf16_offset_map.append(target_utf16_offset_map[-1] + item.utf16_width)
        if isinstance(item, ParagraphBoundary):
            target_paragraph_ranges[position] = (
                paragraph_start,
                target_utf16_offset_map[-1],
            )
            paragraph_start = target_utf16_offset_map[-1]

    edits: list[Edit] = []
    opcodes = SequenceMatcher(
        a=source_values,
        b=target_values,
        autojunk=False,
    ).get_opcodes()

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
    for tag, source_start, source_end, target_start, target_end in reversed(opcodes):
        index = source_utf16_offset_map[source_start]
        # A replacement deletes first so its insertion can reuse the same index.
        if tag in {"delete", "replace"}:
            edits.append(
                DeleteContent(
                    start_index=index,
                    end_index=source_utf16_offset_map[source_end],
                )
            )
        if tag in {"insert", "replace"}:
            text = "".join(
                item.content if isinstance(item, TextUnit) else "\n"
                for item in target.items[target_start:target_end]
            )
            edits.append(InsertText(index=index, text=text))

    # Content edits leave the document with the target shape, so style edits can
    # now use target indices. Equal opcodes provide a source style to compare;
    # inserted and replaced target items have no dependable inherited style.
    for tag, source_start, _source_end, target_start, target_end in opcodes:
        for target_position in range(target_start, target_end):
            target_item = target.items[target_position]
            source_item = None
            if tag == "equal":
                source_item = source.items[
                    source_start + target_position - target_start
                ]

            start_index = target_utf16_offset_map[target_position]
            end_index = target_utf16_offset_map[target_position + 1]
            if isinstance(target_item, TextUnit):
                if (
                    source_item is None
                    or source_item.text_style != target_item.text_style
                ):
                    edits.append(
                        ApplyTextStyle(
                            start_index=start_index,
                            end_index=end_index,
                            text_style=target_item.text_style,
                        )
                    )
                continue

            # A boundary carries both the text style of its newline and the
            # paragraph style of the paragraph that ends there.
            if source_item is None or source_item.text_style != target_item.text_style:
                edits.append(
                    ApplyTextStyle(
                        start_index=start_index,
                        end_index=end_index,
                        text_style=target_item.text_style,
                    )
                )
            source_boundary = (
                source_item if isinstance(source_item, ParagraphBoundary) else None
            )
            if (
                target_position in forced_paragraph_style_positions
                or source_boundary is None
                or source_boundary.paragraph_style != target_item.paragraph_style
            ):
                paragraph_start, paragraph_end = target_paragraph_ranges[
                    target_position
                ]
                edits.append(
                    ApplyParagraphStyle(
                        start_index=paragraph_start,
                        end_index=paragraph_end,
                        paragraph_style=target_item.paragraph_style,
                    )
                )

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
