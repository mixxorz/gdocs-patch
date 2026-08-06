from gdocs_patch.compiler import (
    ApplyParagraphStyle,
    ApplyTextStyle,
    ContentStream,
    DeleteContent,
    InsertText,
    ParagraphBoundary,
    TextUnit,
    generate_edit_script,
)
from gdocs_patch.models import UNSET, ParagraphStyle, TextStyle


def test_generate_edit_script_handles_longer_content_and_style_ranges() -> None:
    # Source content is "Hello XXX 🌍world\n" with a normal paragraph style.
    # The replacement covers several characters rather than a single unit.
    source = ContentStream(
        items=[
            TextUnit(content="H"),
            TextUnit(content="e"),
            TextUnit(content="l"),
            TextUnit(content="l"),
            TextUnit(content="o"),
            TextUnit(content=" "),
            TextUnit(content="X"),
            TextUnit(content="X"),
            TextUnit(content="X"),
            TextUnit(content=" "),
            TextUnit(content="🌍"),
            TextUnit(content="w"),
            TextUnit(content="o"),
            TextUnit(content="r"),
            TextUnit(content="l"),
            TextUnit(content="d"),
            ParagraphBoundary(
                paragraph_style=ParagraphStyle(named_style_type="NORMAL_TEXT")
            ),
        ]
    )

    # Target content is "Hello abcdef 🌍world\n". "world" becomes italic and
    # the paragraph becomes a heading. The emoji occupies two UTF-16 code units,
    # making the final ranges "abcdef" 6..12, "world" 15..20, and the complete
    # paragraph 0..21.
    target_text_style = TextStyle(italic=True)
    target_paragraph_style = ParagraphStyle(named_style_type="HEADING_1")
    target = ContentStream(
        items=[
            TextUnit(content="H"),
            TextUnit(content="e"),
            TextUnit(content="l"),
            TextUnit(content="l"),
            TextUnit(content="o"),
            TextUnit(content=" "),
            TextUnit(content="a"),
            TextUnit(content="b"),
            TextUnit(content="c"),
            TextUnit(content="d"),
            TextUnit(content="e"),
            TextUnit(content="f"),
            TextUnit(content=" "),
            TextUnit(content="🌍"),
            TextUnit(content="w", text_style=target_text_style),
            TextUnit(content="o", text_style=target_text_style),
            TextUnit(content="r", text_style=target_text_style),
            TextUnit(content="l", text_style=target_text_style),
            TextUnit(content="d", text_style=target_text_style),
            ParagraphBoundary(paragraph_style=target_paragraph_style),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [
        # Replacements delete before inserting so both operations can use the
        # original source start index.
        DeleteContent(start_index=6, end_index=9),
        InsertText(index=6, text="abcdef"),
        # Adjacent ranges with the same target style are collapsed.
        ApplyTextStyle(start_index=6, end_index=12, text_style=UNSET),
        ApplyTextStyle(
            start_index=15,
            end_index=20,
            text_style=target_text_style,
        ),
        ApplyParagraphStyle(
            start_index=0,
            end_index=21,
            paragraph_style=target_paragraph_style,
        ),
    ]
