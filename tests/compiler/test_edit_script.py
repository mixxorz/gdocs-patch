import pytest

from gdocs_patch.compiler import (
    ApplyBulletRun,
    ApplyParagraphStyle,
    ApplySectionStyle,
    ApplyTextStyle,
    BulletParagraph,
    BulletPreset,
    ContentStream,
    DeleteContent,
    DeleteParagraphBullets,
    DeleteSectionBreak,
    EquationUnit,
    InsertSectionBreak,
    InsertTable,
    InsertTableRow,
    InsertText,
    OpaqueUnit,
    ParagraphBoundary,
    SectionBreakUnit,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
    UnsupportedTransformation,
    generate_edit_script,
)
from gdocs_patch.models import (
    UNSET,
    Bullet,
    Dimension,
    ParagraphStyle,
    SectionStyle,
    TextStyle,
)


def test_generate_edit_script_inserts_two_table_rows() -> None:
    # Duplicate row and cell keys are allowed. Matching deterministically
    # retains the first two rows and treats the final two target rows as inserted.
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table-1",
                rows=[
                    TableRowUnit(
                        row_key="row",
                        cells=[
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="B"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row",
                        cells=[
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="C"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="D"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                ],
            )
        ]
    )
    target = ContentStream(
        items=[
            TableUnit(
                table_key="table-1",
                rows=[
                    TableRowUnit(
                        row_key="row",
                        cells=[
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="B"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row",
                        cells=[
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="C"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="cell",
                                content=ContentStream(
                                    items=[TextUnit(content="D"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        cells=[
                            TableCellUnit(
                                content=ContentStream(
                                    items=[TextUnit(content="E"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                content=ContentStream(
                                    items=[TextUnit(content="F"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        cells=[
                            TableCellUnit(
                                content=ContentStream(
                                    items=[TextUnit(content="G"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                content=ContentStream(
                                    items=[
                                        TextUnit(content="H"),
                                        ParagraphBoundary(
                                            paragraph_style=ParagraphStyle(
                                                alignment="CENTER"
                                            )
                                        ),
                                    ]
                                ),
                            ),
                        ],
                    ),
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [
        InsertTableRow(
            table_start_index=0,
            row_index=1,
            column_index=0,
            insert_below=True,
        ),
        InsertTableRow(
            table_start_index=0,
            row_index=2,
            column_index=0,
            insert_below=True,
        ),
        # Populate cells from right to left so earlier insertions cannot shift
        # the indices of cells that have not been populated yet.
        InsertText(index=24, text="H"),
        InsertText(index=22, text="G"),
        InsertText(index=19, text="F"),
        InsertText(index=17, text="E"),
        ApplyParagraphStyle(
            start_index=27,
            end_index=29,
            paragraph_style=ParagraphStyle(alignment="CENTER"),
            inside_table=True,
        ),
        ApplyTextStyle(start_index=27, end_index=28, text_style=UNSET),
        ApplyTextStyle(start_index=24, end_index=25, text_style=UNSET),
        ApplyTextStyle(start_index=20, end_index=21, text_style=UNSET),
        ApplyTextStyle(start_index=17, end_index=18, text_style=UNSET),
    ]


def test_generate_edit_script_inserts_table_between_existing_paragraphs() -> None:
    initial_section = SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS"))
    empty_table = TableUnit(
        rows=[
            TableRowUnit(
                cells=[
                    TableCellUnit(content=ContentStream(items=[ParagraphBoundary()]))
                ]
            )
        ]
    )
    source = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            empty_table,
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )

    assert generate_edit_script(source=source, target=target).edits == [
        InsertTable(
            index=3,
            rows=1,
            columns=1,
            preceding_boundary="RETAINED",
        )
    ]


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
        ApplyParagraphStyle(
            start_index=0,
            end_index=21,
            paragraph_style=target_paragraph_style,
        ),
        # Text styles come after paragraph styles because applying a named
        # paragraph style can reset inline formatting.
        ApplyTextStyle(start_index=6, end_index=12, text_style=UNSET),
        ApplyTextStyle(
            start_index=15,
            end_index=20,
            text_style=target_text_style,
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
        ApplyBulletRun(
            paragraphs=(
                BulletParagraph(
                    start_index=12,
                    end_index=19,
                    nesting_level=0,
                ),
                BulletParagraph(
                    start_index=19,
                    end_index=25,
                    nesting_level=1,
                ),
            ),
            preset="BULLET_DISC_CIRCLE_SQUARE",
        ),
    ]

    with pytest.raises(
        UnsupportedTransformation,
        match="moving paragraphs between existing lists is not supported",
    ):
        generate_edit_script(
            source=ContentStream(
                items=[
                    TextUnit(content="Existing"),
                    ParagraphBoundary(bullet=Bullet(list_id="list-source")),
                ]
            ),
            target=ContentStream(
                items=[
                    TextUnit(content="Existing"),
                    ParagraphBoundary(bullet=Bullet(list_id="list-target")),
                ]
            ),
        )


def test_generate_edit_script_preserves_and_deletes_equations() -> None:
    source = ContentStream(
        items=[
            TextUnit(content="A"),
            OpaqueUnit(key="opaque-retained", width=2, is_inline=True),
            EquationUnit(),
            TextUnit(content="B"),
            OpaqueUnit(key="opaque-deleted", width=3, is_inline=False),
            EquationUnit(),
            TextUnit(content="C"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            TextUnit(content="A"),
            OpaqueUnit(key="opaque-retained", width=2, is_inline=True),
            EquationUnit(),
            TextUnit(content="B"),
            TextUnit(content="C"),
            ParagraphBoundary(),
        ]
    )

    script = generate_edit_script(source=source, target=target)

    assert script.edits == [DeleteContent(start_index=5, end_index=9)]


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

    with pytest.raises(UnsupportedTransformation, match="OpaqueUnit"):
        generate_edit_script(
            source=ContentStream(
                items=[
                    TextUnit(content="A"),
                    TextUnit(content="B"),
                    ParagraphBoundary(),
                ]
            ),
            target=ContentStream(
                items=[
                    TextUnit(content="A"),
                    OpaqueUnit(key="opaque-new", width=1, is_inline=True),
                    TextUnit(content="B"),
                    ParagraphBoundary(),
                ]
            ),
        )


def test_generate_edit_script_inserts_section_break_with_inserted_boundary() -> None:
    source = ContentStream(
        items=[
            SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
            TextUnit(content="A"),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
            TextUnit(content="A"),
            ParagraphBoundary(),
            SectionBreakUnit(style=SectionStyle(section_type="NEXT_PAGE")),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )

    assert generate_edit_script(source=source, target=target).edits == [
        InsertSectionBreak(
            index=3,
            section_type="NEXT_PAGE",
            preceding_boundary="INSERTED",
        )
    ]


def test_generate_edit_script_inserts_section_break_after_retained_boundary() -> None:
    initial_section = SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS"))
    source = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )

    assert generate_edit_script(source=source, target=target).edits == [
        InsertSectionBreak(
            index=3,
            section_type="CONTINUOUS",
            preceding_boundary="RETAINED",
        )
    ]


def test_generate_edit_script_deletes_section_break_after_retained_boundary() -> None:
    initial_section = SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS"))
    source = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS")),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )
    target = ContentStream(
        items=[
            initial_section,
            TextUnit(content="A"),
            ParagraphBoundary(),
            TextUnit(content="B"),
            ParagraphBoundary(),
        ]
    )

    assert generate_edit_script(source=source, target=target).edits == [
        DeleteSectionBreak(index=3)
    ]


def test_generate_edit_script_applies_retained_section_style() -> None:
    source_style = SectionStyle(
        section_type="CONTINUOUS",
        margin_left=Dimension(magnitude=72, unit="PT"),
        default_header_id="source-header",
    )
    target_style = SectionStyle(
        section_type="CONTINUOUS",
        margin_left=Dimension(magnitude=90, unit="PT"),
        default_header_id="target-header",
    )

    assert generate_edit_script(
        source=ContentStream(items=[SectionBreakUnit(style=source_style)]),
        target=ContentStream(items=[SectionBreakUnit(style=target_style)]),
    ).edits == [
        ApplySectionStyle(
            start_index=0,
            end_index=1,
            section_style=target_style,
        )
    ]


def test_generate_edit_script_rejects_retained_section_type_change() -> None:
    with pytest.raises(UnsupportedTransformation):
        generate_edit_script(
            source=ContentStream(
                items=[SectionBreakUnit(style=SectionStyle(section_type="CONTINUOUS"))]
            ),
            target=ContentStream(
                items=[SectionBreakUnit(style=SectionStyle(section_type="NEXT_PAGE"))]
            ),
        )


def test_generate_edit_script_rejects_clearing_concrete_section_style() -> None:
    with pytest.raises(UnsupportedTransformation):
        generate_edit_script(
            source=ContentStream(
                items=[
                    SectionBreakUnit(
                        style=SectionStyle(
                            section_type="CONTINUOUS",
                            margin_left=Dimension(magnitude=72, unit="PT"),
                        )
                    )
                ]
            ),
            target=ContentStream(
                items=[
                    SectionBreakUnit(
                        style=SectionStyle(
                            section_type="CONTINUOUS",
                            margin_left=UNSET,
                        )
                    )
                ]
            ),
        )
