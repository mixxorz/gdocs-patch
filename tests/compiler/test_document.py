from gdocs_patch.compiler import (
    ContentStream,
    EquationUnit,
    ParagraphBoundary,
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

    assert len(stream.items) == 4
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "A"
    assert stream.items[0].text_style is first_style
    assert isinstance(stream.items[1], TextUnit)
    assert stream.items[1].content == "\n"
    assert stream.items[1].text_style is first_style
    assert isinstance(stream.items[2], TextUnit)
    assert stream.items[2].content == "🌍"
    assert stream.items[2].text_style is final_style
    assert isinstance(stream.items[3], ParagraphBoundary)
    assert stream.items[3].text_style is final_style
    assert stream.items[3].paragraph_style is paragraph_style
    assert stream.items[3].bullet is bullet


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

    assert len(stream.items) == 1
    table_unit = stream.items[0]
    assert isinstance(table_unit, TableUnit)
    assert table_unit.table_key == "table-abcdef"
    assert table_unit.column_properties == [fixed_column, even_column]
    assert len(table_unit.rows) == 2

    header_row = table_unit.rows[0]
    assert header_row.row_key == "row-header"
    assert header_row.min_height == Dimension(magnitude=24, unit="PT")
    assert header_row.prevent_overflow is True
    assert header_row.is_header is True
    assert len(header_row.cells) == 1
    assert header_row.cells[0].cell_key == "cell-header"
    assert header_row.cells[0].row_span == 1
    assert header_row.cells[0].column_span == 2
    assert header_row.cells[0].style is header_style
    assert len(header_row.cells[0].content.items) == 5
    assert isinstance(header_row.cells[0].content.items[0], TextUnit)
    assert header_row.cells[0].content.items[0].content == "H"
    assert isinstance(header_row.cells[0].content.items[4], ParagraphBoundary)

    body_row = table_unit.rows[1]
    assert body_row.row_key == "row-body"
    assert body_row.min_height is UNSET
    assert body_row.prevent_overflow is False
    assert body_row.is_header is UNSET
    assert len(body_row.cells) == 2
    assert body_row.cells[0].cell_key == "cell-left"
    assert body_row.cells[0].row_span == 1
    assert body_row.cells[0].column_span == 1
    assert body_row.cells[0].style is left_style
    assert len(body_row.cells[0].content.items) == 2
    assert isinstance(body_row.cells[0].content.items[0], TextUnit)
    assert body_row.cells[0].content.items[0].content == "L"
    assert isinstance(body_row.cells[0].content.items[1], ParagraphBoundary)
    assert body_row.cells[1].cell_key == "cell-right"
    assert body_row.cells[1].row_span == 1
    assert body_row.cells[1].column_span == 1
    assert body_row.cells[1].style is UNSET
    assert len(body_row.cells[1].content.items) == 6
    assert isinstance(body_row.cells[1].content.items[0], TextUnit)
    assert body_row.cells[1].content.items[0].content == "R"
    assert isinstance(body_row.cells[1].content.items[2], ParagraphBoundary)
    assert isinstance(body_row.cells[1].content.items[3], TextUnit)
    assert body_row.cells[1].content.items[3].content == "R"
    assert isinstance(body_row.cells[1].content.items[5], ParagraphBoundary)


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

    assert len(stream.items) == 4
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "A"
    assert isinstance(stream.items[1], EquationUnit)
    assert isinstance(stream.items[2], TextUnit)
    assert stream.items[2].content == "B"
    assert stream.items[2].text_style is final_style
    assert isinstance(stream.items[3], ParagraphBoundary)
    assert stream.items[3].text_style is final_style


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

    assert len(stream.items) == 7
    assert isinstance(stream.items[0], TextUnit)
    assert stream.items[0].content == "G"
    assert isinstance(stream.items[1], TextUnit)
    assert stream.items[1].content == "o"
    assert isinstance(stream.items[2], ParagraphBoundary)
    assert stream.items[2].bullet is bullet
    assert isinstance(stream.items[3], TableUnit)
    assert stream.items[3].table_key == "table-kitchen"
    assert stream.items[3].rows[0].row_key == "row-kitchen"
    assert stream.items[3].rows[0].cells[0].cell_key == "cell-kitchen"
    assert isinstance(stream.items[3].rows[0].cells[0].content, ContentStream)
    assert len(stream.items[3].rows[0].cells[0].content.items) == 2
    assert isinstance(stream.items[3].rows[0].cells[0].content.items[0], TextUnit)
    assert stream.items[3].rows[0].cells[0].content.items[0].content == "T"
    assert isinstance(
        stream.items[3].rows[0].cells[0].content.items[1], ParagraphBoundary
    )
    assert isinstance(stream.items[4], TextUnit)
    assert stream.items[4].content == "X"
    assert isinstance(stream.items[5], EquationUnit)
    assert isinstance(stream.items[6], ParagraphBoundary)
