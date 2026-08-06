from gdocs_patch.compiler.content_stream import (
    ContentStream,
    ParagraphBoundary,
    TextUnit,
)


def test_content_stream_measures_utf16_content() -> None:
    stream = ContentStream(
        items=[
            TextUnit(content="A"),
            TextUnit(content="🌍"),
            ParagraphBoundary(),
        ]
    )

    assert [item.utf16_width for item in stream.items] == [1, 2, 1]
    assert stream.utf16_width == 4
