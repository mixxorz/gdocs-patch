from gdocs_patch.compiler import (
    ContentStream,
    DeleteContent,
    InsertText,
    ParagraphBoundary,
    TextUnit,
    generate_edit_script,
)


def test_generate_edit_script_orders_edits_from_right_to_left() -> None:
    source = ContentStream(
        items=[
            TextUnit(content="A"),
            TextUnit(content="X"),
            TextUnit(content="🌍"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            TextUnit(content="A"),
            TextUnit(content="🌍"),
            TextUnit(content="!"),
            ParagraphBoundary(),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert len(script.edits) == 2

    insert = script.edits[0]
    assert isinstance(insert, InsertText)
    assert insert.index == 4
    assert insert.text == "!"

    delete = script.edits[1]
    assert isinstance(delete, DeleteContent)
    assert delete.start_index == 1
    assert delete.end_index == 2
