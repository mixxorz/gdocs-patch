import pytest

from gdocs_patch.compiler import (
    ApplyParagraphStyle,
    ApplyTextStyle,
    BulletPreset,
    ContentStream,
    CreateParagraphBullets,
    DeleteContent,
    DeleteParagraphBullets,
    EquationUnit,
    InsertText,
    ParagraphBoundary,
    TextUnit,
    UnsupportedTransformation,
    generate_edit_script,
)
from gdocs_patch.models import UNSET, Bullet, ParagraphStyle, TextStyle


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


def test_generate_edit_script_reapplies_style_after_merging_paragraphs() -> None:
    # Deleting two boundaries merges three paragraphs. Google may retain a
    # heading style even though the matched surviving boundary already has the
    # target's normal style.
    first_heading_style = ParagraphStyle(named_style_type="HEADING_1")
    second_heading_style = ParagraphStyle(named_style_type="HEADING_2")
    normal_style = ParagraphStyle(named_style_type="NORMAL_TEXT")
    source = ContentStream(
        items=[
            TextUnit(content="H"),
            TextUnit(content="e"),
            TextUnit(content="l"),
            TextUnit(content="l"),
            TextUnit(content="o"),
            ParagraphBoundary(paragraph_style=first_heading_style),
            TextUnit(content="w"),
            TextUnit(content="o"),
            TextUnit(content="r"),
            TextUnit(content="l"),
            TextUnit(content="d"),
            ParagraphBoundary(paragraph_style=second_heading_style),
            TextUnit(content="a"),
            TextUnit(content="g"),
            TextUnit(content="a"),
            TextUnit(content="i"),
            TextUnit(content="n"),
            ParagraphBoundary(paragraph_style=normal_style),
        ]
    )
    target = ContentStream(
        items=[
            TextUnit(content="H"),
            TextUnit(content="e"),
            TextUnit(content="l"),
            TextUnit(content="l"),
            TextUnit(content="o"),
            TextUnit(content="w"),
            TextUnit(content="o"),
            TextUnit(content="r"),
            TextUnit(content="l"),
            TextUnit(content="d"),
            TextUnit(content="a"),
            TextUnit(content="g"),
            TextUnit(content="a"),
            TextUnit(content="i"),
            TextUnit(content="n"),
            ParagraphBoundary(paragraph_style=normal_style),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [
        DeleteContent(start_index=11, end_index=12),
        DeleteContent(start_index=5, end_index=6),
        ApplyParagraphStyle(
            start_index=0,
            end_index=16,
            paragraph_style=normal_style,
        ),
    ]


def test_generate_edit_script_preserves_removes_and_creates_list_items() -> None:
    existing_parent_bullet = Bullet(list_id="list-1", nesting_level=0)
    existing_child_bullet = Bullet(list_id="list-1", nesting_level=1)
    source = ContentStream(
        items=[
            TextUnit(content="K"),
            TextUnit(content="e"),
            TextUnit(content="e"),
            TextUnit(content="p"),
            ParagraphBoundary(bullet=existing_parent_bullet),
            TextUnit(content="R"),
            TextUnit(content="e"),
            TextUnit(content="m"),
            TextUnit(content="o"),
            TextUnit(content="v"),
            TextUnit(content="e"),
            ParagraphBoundary(bullet=existing_child_bullet),
            TextUnit(content="P"),
            TextUnit(content="a"),
            TextUnit(content="r"),
            TextUnit(content="e"),
            TextUnit(content="n"),
            TextUnit(content="t"),
            ParagraphBoundary(),
            TextUnit(content="C"),
            TextUnit(content="h"),
            TextUnit(content="i"),
            TextUnit(content="l"),
            TextUnit(content="d"),
            ParagraphBoundary(),
        ]
    )

    # The existing parent item remains in list-1, its nested child becomes a
    # normal paragraph, and a new two-level list is created from normal text.
    parent_preset = BulletPreset(
        preset="BULLET_DISC_CIRCLE_SQUARE",
        nesting_level=0,
    )
    child_preset = BulletPreset(
        preset="BULLET_DISC_CIRCLE_SQUARE",
        nesting_level=1,
    )
    target = ContentStream(
        items=[
            TextUnit(content="K"),
            TextUnit(content="e"),
            TextUnit(content="e"),
            TextUnit(content="p"),
            ParagraphBoundary(bullet=existing_parent_bullet),
            TextUnit(content="R"),
            TextUnit(content="e"),
            TextUnit(content="m"),
            TextUnit(content="o"),
            TextUnit(content="v"),
            TextUnit(content="e"),
            ParagraphBoundary(),
            TextUnit(content="P"),
            TextUnit(content="a"),
            TextUnit(content="r"),
            TextUnit(content="e"),
            TextUnit(content="n"),
            TextUnit(content="t"),
            ParagraphBoundary(bullet=parent_preset),
            TextUnit(content="C"),
            TextUnit(content="h"),
            TextUnit(content="i"),
            TextUnit(content="l"),
            TextUnit(content="d"),
            ParagraphBoundary(bullet=child_preset),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [
        DeleteParagraphBullets(start_index=5, end_index=12),
        CreateParagraphBullets(
            start_index=12,
            end_index=19,
            bullet_preset=parent_preset,
        ),
        CreateParagraphBullets(
            start_index=19,
            end_index=25,
            bullet_preset=child_preset,
        ),
    ]


def test_generate_edit_script_preserves_and_deletes_equations() -> None:
    source = ContentStream(
        items=[
            TextUnit(content="A"),
            EquationUnit(),
            TextUnit(content="B"),
            EquationUnit(),
            TextUnit(content="C"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            TextUnit(content="A"),
            EquationUnit(),
            TextUnit(content="B"),
            TextUnit(content="C"),
            ParagraphBoundary(),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [DeleteContent(start_index=3, end_index=4)]


def test_generate_edit_script_rejects_equation_insertion() -> None:
    source = ContentStream(
        items=[
            TextUnit(content="A"),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            TextUnit(content="A"),
            EquationUnit(),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )

    with pytest.raises(UnsupportedTransformation, match="Equation"):
        generate_edit_script(source=source, target=target)
