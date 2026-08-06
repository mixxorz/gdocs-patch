from difflib import SequenceMatcher

from .content_stream import ContentStream, TextUnit


class InsertText:
    def __init__(self, *, index: int, text: str) -> None:
        self.index = index
        self.text = text


class DeleteContent:
    def __init__(self, *, start_index: int, end_index: int) -> None:
        self.start_index = start_index
        self.end_index = end_index


class EditScript:
    def __init__(self, *, edits: list[InsertText | DeleteContent]) -> None:
        self.edits = edits


def generate_edit_script(*, source: ContentStream, target: ContentStream) -> EditScript:
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

    source_utf16_offsets = [0]
    for item in source.items:
        source_utf16_offsets.append(source_utf16_offsets[-1] + item.utf16_width)

    edits: list[InsertText | DeleteContent] = []
    opcodes = SequenceMatcher(
        a=source_values,
        b=target_values,
        autojunk=False,
    ).get_opcodes()
    for tag, source_start, source_end, target_start, target_end in reversed(opcodes):
        index = source_utf16_offsets[source_start]
        if tag in {"delete", "replace"}:
            edits.append(
                DeleteContent(
                    start_index=index,
                    end_index=source_utf16_offsets[source_end],
                )
            )
        if tag in {"insert", "replace"}:
            text = "".join(
                item.content if isinstance(item, TextUnit) else "\n"
                for item in target.items[target_start:target_end]
            )
            edits.append(InsertText(index=index, text=text))

    return EditScript(edits=edits)
