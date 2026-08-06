from gdocs_patch.compiler import (
    ContentStream,
    DeleteTableColumn,
    DeleteTableRow,
    InsertTableColumn,
    InsertText,
    MergeTableCells,
    ParagraphBoundary,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
    UnmergeTableCells,
    generate_edit_script,
)


def test_generate_edit_script_inserts_a_table_column() -> None:
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="row-1",
                        cells=[
                            TableCellUnit(
                                cell_key="a",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="c",
                                content=ContentStream(
                                    items=[TextUnit(content="C"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-2",
                        cells=[
                            TableCellUnit(
                                cell_key="d",
                                content=ContentStream(
                                    items=[TextUnit(content="D"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="f",
                                content=ContentStream(
                                    items=[TextUnit(content="F"), ParagraphBoundary()]
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
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="row-1",
                        cells=[
                            TableCellUnit(
                                cell_key="a",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                content=ContentStream(
                                    items=[TextUnit(content="B"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="c",
                                content=ContentStream(
                                    items=[TextUnit(content="C"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-2",
                        cells=[
                            TableCellUnit(
                                cell_key="d",
                                content=ContentStream(
                                    items=[TextUnit(content="D"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                content=ContentStream(
                                    items=[TextUnit(content="E"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="f",
                                content=ContentStream(
                                    items=[TextUnit(content="F"), ParagraphBoundary()]
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
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_right=True,
        ),
        InsertText(index=6, text="B"),
        InsertText(index=16, text="E"),
    ]


def test_generate_edit_script_deletes_a_table_row() -> None:
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="row-1",
                        cells=[
                            TableCellUnit(
                                cell_key="a",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="b",
                                content=ContentStream(
                                    items=[TextUnit(content="B"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-2",
                        cells=[
                            TableCellUnit(
                                cell_key="c",
                                content=ContentStream(
                                    items=[TextUnit(content="C"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="d",
                                content=ContentStream(
                                    items=[TextUnit(content="D"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-3",
                        cells=[
                            TableCellUnit(
                                cell_key="e",
                                content=ContentStream(
                                    items=[TextUnit(content="E"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="f",
                                content=ContentStream(
                                    items=[TextUnit(content="F"), ParagraphBoundary()]
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
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="row-1",
                        cells=[
                            TableCellUnit(
                                cell_key="a",
                                content=ContentStream(
                                    items=[TextUnit(content="A"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="b",
                                content=ContentStream(
                                    items=[TextUnit(content="B"), ParagraphBoundary()]
                                ),
                            ),
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-3",
                        cells=[
                            TableCellUnit(
                                cell_key="e",
                                content=ContentStream(
                                    items=[TextUnit(content="E"), ParagraphBoundary()]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="f",
                                content=ContentStream(
                                    items=[TextUnit(content="F"), ParagraphBoundary()]
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
        DeleteTableRow(table_start_index=0, row_index=1, column_index=0)
    ]


def test_generate_edit_script_deletes_a_table_column() -> None:
    source_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(
                            items=[TextUnit(content="A"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(
                            items=[TextUnit(content="B"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="e",
                        content=ContentStream(
                            items=[TextUnit(content="E"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="f",
                        content=ContentStream(
                            items=[TextUnit(content="F"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )
    target_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(
                            items=[TextUnit(content="A"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="f",
                        content=ContentStream(
                            items=[TextUnit(content="F"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )

    script = generate_edit_script(
        source=ContentStream(items=[source_table]),
        target=ContentStream(items=[target_table]),
    )

    assert script.edits == [
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=1)
    ]


def test_generate_edit_script_merges_table_cells() -> None:
    source_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(
                            items=[TextUnit(content="A"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(
                            items=[TextUnit(content="B"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )
    target_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        column_span=2,
                        content=ContentStream(
                            items=[
                                TextUnit(content="A"),
                                ParagraphBoundary(),
                                TextUnit(content="B"),
                                ParagraphBoundary(),
                            ]
                        ),
                    )
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )

    script = generate_edit_script(
        source=ContentStream(items=[source_table]),
        target=ContentStream(items=[target_table]),
    )

    assert script.edits == [
        MergeTableCells(
            table_start_index=0,
            row_index=0,
            column_index=0,
            row_span=1,
            column_span=2,
        )
    ]


def test_generate_edit_script_unmerges_table_cells() -> None:
    source_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        column_span=2,
                        content=ContentStream(
                            items=[
                                TextUnit(content="A"),
                                ParagraphBoundary(),
                                TextUnit(content="B"),
                                ParagraphBoundary(),
                            ]
                        ),
                    )
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )
    target_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(
                            items=[
                                TextUnit(content="A"),
                                ParagraphBoundary(),
                                TextUnit(content="B"),
                                ParagraphBoundary(),
                            ]
                        ),
                    ),
                    TableCellUnit(
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(
                            items=[TextUnit(content="C"), ParagraphBoundary()]
                        ),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[TextUnit(content="D"), ParagraphBoundary()]
                        ),
                    ),
                ],
            ),
        ],
    )

    script = generate_edit_script(
        source=ContentStream(items=[source_table]),
        target=ContentStream(items=[target_table]),
    )

    assert script.edits == [
        UnmergeTableCells(
            table_start_index=0,
            row_index=0,
            column_index=0,
            row_span=1,
            column_span=2,
        )
    ]
