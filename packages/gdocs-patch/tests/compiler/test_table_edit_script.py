from gdocs_patch.compiler import (
    ApplyParagraphStyle,
    ApplyTableCellStyle,
    ApplyTableColumnProperties,
    ApplyTableRowStyle,
    ApplyTextStyle,
    ContentStream,
    DeleteContent,
    DeleteTableColumn,
    DeleteTableRow,
    InsertTableColumn,
    InsertTableRow,
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
from gdocs_patch.models import UNSET, Color, Dimension, TableCellStyle, TableColumn


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
        InsertText(index=15, text="E"),
        InsertText(index=6, text="B"),
        ApplyTextStyle(start_index=16, end_index=17, text_style=UNSET),
        ApplyTextStyle(start_index=6, end_index=7, text_style=UNSET),
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


def test_generate_edit_script_reconciles_mixed_table_rows() -> None:
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            )
                        ],
                    ),
                    TableRowUnit(
                        row_key="removed-row-1",
                        cells=[TableCellUnit(content=empty_content)],
                    ),
                    TableRowUnit(
                        row_key="removed-row-2",
                        cells=[TableCellUnit(content=empty_content)],
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
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            )
                        ],
                    ),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableRow, InsertTableRow))
    ]

    assert structural_edits == [
        DeleteTableRow(table_start_index=0, row_index=2, column_index=0),
        DeleteTableRow(table_start_index=0, row_index=1, column_index=0),
        InsertTableRow(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_below=True,
        ),
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
    ]


def test_generate_edit_script_replaces_all_table_rows_before_deleting_anchor() -> None:
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="removed-row-1",
                        cells=[TableCellUnit(content=empty_content)],
                    ),
                    TableRowUnit(
                        row_key="removed-row-2",
                        cells=[TableCellUnit(content=empty_content)],
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
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                    TableRowUnit(cells=[TableCellUnit(content=empty_content)]),
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableRow, InsertTableRow))
    ]

    assert structural_edits == [
        DeleteTableRow(table_start_index=0, row_index=1, column_index=0),
        InsertTableRow(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_below=False,
        ),
        InsertTableRow(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_below=True,
        ),
        DeleteTableRow(table_start_index=0, row_index=2, column_index=0),
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


def test_generate_edit_script_reconciles_mixed_table_columns() -> None:
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            ),
                            TableCellUnit(
                                cell_key="removed-cell-1",
                                content=empty_content,
                            ),
                            TableCellUnit(
                                cell_key="removed-cell-2",
                                content=empty_content,
                            ),
                        ],
                    )
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
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="retained-cell",
                                content=empty_content,
                            ),
                            TableCellUnit(content=empty_content),
                            TableCellUnit(content=empty_content),
                            TableCellUnit(content=empty_content),
                        ],
                    )
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableColumn, InsertTableColumn))
    ]

    assert structural_edits == [
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=2),
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=1),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_right=True,
        ),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=1,
            insert_right=True,
        ),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=2,
            insert_right=True,
        ),
    ]


def test_generate_edit_script_replaces_all_table_columns_before_deleting_anchor() -> (
    None
):
    empty_content = ContentStream(items=[ParagraphBoundary()])
    source = ContentStream(
        items=[
            TableUnit(
                table_key="table",
                rows=[
                    TableRowUnit(
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(
                                cell_key="removed-cell-1",
                                content=empty_content,
                            ),
                            TableCellUnit(
                                cell_key="removed-cell-2",
                                content=empty_content,
                            ),
                        ],
                    )
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
                        row_key="retained-row",
                        cells=[
                            TableCellUnit(content=empty_content),
                            TableCellUnit(content=empty_content),
                        ],
                    )
                ],
            )
        ]
    )

    script = generate_edit_script(source=source, target=target)
    structural_edits = [
        edit
        for edit in script.edits
        if isinstance(edit, (DeleteTableColumn, InsertTableColumn))
    ]

    assert structural_edits == [
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=1),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_right=False,
        ),
        InsertTableColumn(
            table_start_index=0,
            row_index=0,
            column_index=0,
            insert_right=True,
        ),
        DeleteTableColumn(table_start_index=0, row_index=0, column_index=2),
    ]


def test_generate_edit_script_merges_table_cells() -> None:
    source_table = TableUnit(
        table_key="table",
        column_properties=[
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
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
        column_properties=[
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
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
                    ),
                    TableCellUnit(
                        cell_key="b",
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
                    ),
                    TableCellUnit(
                        cell_key="b",
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
                        cell_key="b",
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


def test_generate_edit_script_applies_changed_table_column_properties() -> None:
    fixed_width = TableColumn(
        width_type="FIXED_WIDTH",
        width=Dimension(magnitude=144, unit="PT"),
    )
    source_table = TableUnit(
        table_key="table",
        column_properties=[
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
        ],
    )
    target_table = TableUnit(
        table_key="table",
        column_properties=[
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
            fixed_width,
        ],
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(items=[ParagraphBoundary()]),
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
        ApplyTableColumnProperties(
            table_start_index=0,
            column_index=1,
            column_properties=fixed_width,
        )
    ]


def test_generate_edit_script_applies_changed_table_row_style() -> None:
    target_min_height = Dimension(magnitude=36, unit="PT")
    source_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(items=[ParagraphBoundary()]),
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
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                min_height=target_min_height,
                prevent_overflow=True,
                is_header=UNSET,
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(items=[ParagraphBoundary()]),
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
        ApplyTableRowStyle(
            table_start_index=0,
            row_index=1,
            min_height=target_min_height,
            prevent_overflow=True,
            is_header=UNSET,
        )
    ]


def test_generate_edit_script_updates_table_cell_content_and_style() -> None:
    target_cell_style = TableCellStyle(
        background_color=Color(red=0.25, green=0.5, blue=0.75),
        padding_left=Dimension(magnitude=12, unit="PT"),
        content_alignment="MIDDLE",
    )
    source_table = TableUnit(
        table_key="table",
        rows=[
            TableRowUnit(
                row_key="row-1",
                cells=[
                    TableCellUnit(
                        cell_key="a",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        content=ContentStream(
                            items=[
                                TextUnit(content="A"),
                                ParagraphBoundary(),
                                TextUnit(content="B"),
                                ParagraphBoundary(),
                            ]
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
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="b",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                ],
            ),
            TableRowUnit(
                row_key="row-2",
                cells=[
                    TableCellUnit(
                        cell_key="c",
                        content=ContentStream(items=[ParagraphBoundary()]),
                    ),
                    TableCellUnit(
                        cell_key="d",
                        style=target_cell_style,
                        content=ContentStream(
                            items=[TextUnit(content="A"), ParagraphBoundary()]
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
        DeleteContent(start_index=11, end_index=13),
        ApplyParagraphStyle(
            start_index=10,
            end_index=12,
            paragraph_style=UNSET,
            inside_table=True,
        ),
        ApplyTableCellStyle(
            table_start_index=0,
            row_index=1,
            column_index=1,
            row_span=1,
            column_span=1,
            cell_style=target_cell_style,
        ),
    ]
