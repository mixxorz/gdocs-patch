from gdocs_patch.compiler import (
    ContentStream,
    EquationUnit,
    ParagraphBoundary,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
    normalize_tree,
)
from gdocs_patch.models import (
    UNSET,
    Body,
    Bullet,
    Color,
    Dimension,
    Equation,
    Paragraph,
    ParagraphStyle,
    Table,
    TableCell,
    TableCellStyle,
    TableColumn,
    TableRow,
    TextRun,
    TextStyle,
)


def test_normalize_tree_normalizes_paragraph_text_styles_and_bullets() -> None:
    first_style = TextStyle(bold=True)
    final_style = TextStyle(italic=True)
    paragraph_style = ParagraphStyle(alignment="CENTER")
    bullet = Bullet(list_id="list-opaque", nesting_level=1)
    body = Body(
        content=[
            Paragraph(
                elements=[
                    TextRun(content="A\n", text_style=first_style),
                    TextRun(content="🌍\n", text_style=final_style),
                ],
                style=paragraph_style,
                bullet=bullet,
            )
        ]
    )

    stream = normalize_tree(body)

    assert stream == ContentStream(
        items=[
            TextUnit(content="A", text_style=first_style),
            TextUnit(content="\n", text_style=first_style),
            TextUnit(content="🌍", text_style=final_style),
            ParagraphBoundary(
                text_style=final_style,
                paragraph_style=paragraph_style,
                bullet=bullet,
            ),
        ]
    )


def test_normalize_tree_preserves_complex_table_shape_content_and_styles() -> None:
    header_style = TableCellStyle(
        column_span=2,
        background_color=Color(red=0.25, green=0.5, blue=0.75),
    )
    left_style = TableCellStyle(content_alignment="MIDDLE")
    fixed_column = TableColumn(
        width_type="FIXED_WIDTH",
        width=Dimension(magnitude=72, unit="PT"),
    )
    even_column = TableColumn(width_type="EVENLY_DISTRIBUTED")
    table = Table(
        table_key="table-abcdef",
        column_styles=[fixed_column, even_column],
        rows=[
            TableRow(
                row_key="row-header",
                min_height=Dimension(magnitude=24, unit="PT"),
                prevent_overflow=True,
                is_header=True,
                cells=[
                    TableCell(
                        cell_key="cell-header",
                        style=header_style,
                        content=[Paragraph(elements=[TextRun(content="Head\n")])],
                    )
                ],
            ),
            TableRow(
                row_key="row-body",
                prevent_overflow=False,
                cells=[
                    TableCell(
                        cell_key="cell-left",
                        style=left_style,
                        content=[Paragraph(elements=[TextRun(content="L\n")])],
                    ),
                    TableCell(
                        cell_key="cell-right",
                        content=[
                            Paragraph(elements=[TextRun(content="R1\n")]),
                            Paragraph(elements=[TextRun(content="R2\n")]),
                        ],
                    ),
                ],
            ),
        ],
    )

    stream = normalize_tree(Body(content=[table]))

    assert stream == ContentStream(
        items=[
            TableUnit(
                table_key="table-abcdef",
                column_properties=[
                    TableColumn(
                        width_type="FIXED_WIDTH",
                        width=Dimension(magnitude=72, unit="PT"),
                    ),
                    TableColumn(width_type="EVENLY_DISTRIBUTED"),
                ],
                rows=[
                    TableRowUnit(
                        row_key="row-header",
                        min_height=Dimension(magnitude=24, unit="PT"),
                        prevent_overflow=True,
                        is_header=True,
                        cells=[
                            TableCellUnit(
                                cell_key="cell-header",
                                row_span=1,
                                column_span=2,
                                style=TableCellStyle(
                                    column_span=2,
                                    background_color=Color(
                                        red=0.25,
                                        green=0.5,
                                        blue=0.75,
                                    ),
                                ),
                                content=ContentStream(
                                    items=[
                                        TextUnit(content="H"),
                                        TextUnit(content="e"),
                                        TextUnit(content="a"),
                                        TextUnit(content="d"),
                                        ParagraphBoundary(),
                                    ]
                                ),
                            )
                        ],
                    ),
                    TableRowUnit(
                        row_key="row-body",
                        min_height=UNSET,
                        prevent_overflow=False,
                        is_header=UNSET,
                        cells=[
                            TableCellUnit(
                                cell_key="cell-left",
                                row_span=1,
                                column_span=1,
                                style=TableCellStyle(content_alignment="MIDDLE"),
                                content=ContentStream(
                                    items=[
                                        TextUnit(content="L"),
                                        ParagraphBoundary(),
                                    ]
                                ),
                            ),
                            TableCellUnit(
                                cell_key="cell-right",
                                row_span=1,
                                column_span=1,
                                style=UNSET,
                                content=ContentStream(
                                    items=[
                                        TextUnit(content="R"),
                                        TextUnit(content="1"),
                                        ParagraphBoundary(),
                                        TextUnit(content="R"),
                                        TextUnit(content="2"),
                                        ParagraphBoundary(),
                                    ]
                                ),
                            ),
                        ],
                    ),
                ],
            )
        ]
    )


def test_normalize_tree_normalizes_opaque_equations_in_paragraphs() -> None:
    final_style = TextStyle(underline=True)
    body = Body(
        content=[
            Paragraph(
                elements=[
                    TextRun(content="A"),
                    Equation(),
                    TextRun(content="B\n", text_style=final_style),
                ]
            )
        ]
    )

    stream = normalize_tree(body)

    assert stream == ContentStream(
        items=[
            TextUnit(content="A"),
            EquationUnit(),
            TextUnit(content="B", text_style=final_style),
            ParagraphBoundary(text_style=final_style),
        ]
    )


def test_normalize_tree_normalizes_kitchen_sink_body_in_document_order() -> None:
    bullet = Bullet(list_id="list-kitchen")
    table = Table(
        table_key="table-kitchen",
        rows=[
            TableRow(
                row_key="row-kitchen",
                cells=[
                    TableCell(
                        cell_key="cell-kitchen",
                        content=[Paragraph(elements=[TextRun(content="T\n")])],
                    )
                ],
            )
        ],
    )
    body = Body(
        content=[
            Paragraph(
                elements=[TextRun(content="Go\n")],
                bullet=bullet,
            ),
            table,
            Paragraph(
                elements=[TextRun(content="X"), Equation(), TextRun(content="\n")]
            ),
        ]
    )

    stream = normalize_tree(body)

    assert stream == ContentStream(
        items=[
            TextUnit(content="G"),
            TextUnit(content="o"),
            ParagraphBoundary(bullet=bullet),
            TableUnit(
                table_key="table-kitchen",
                rows=[
                    TableRowUnit(
                        row_key="row-kitchen",
                        cells=[
                            TableCellUnit(
                                cell_key="cell-kitchen",
                                content=ContentStream(
                                    items=[
                                        TextUnit(content="T"),
                                        ParagraphBoundary(),
                                    ]
                                ),
                            )
                        ],
                    )
                ],
            ),
            TextUnit(content="X"),
            EquationUnit(),
            ParagraphBoundary(),
        ]
    )
