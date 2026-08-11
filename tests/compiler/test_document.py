import pytest

from gdocs_patch.compiler import (
    ContentStream,
    DocumentContent,
    EquationUnit,
    ParagraphBoundary,
    TabContent,
    TableCellUnit,
    TableRowUnit,
    TableUnit,
    TextUnit,
    UnsupportedTransformation,
    compile_document,
    normalize_document,
    normalize_tree,
)
from gdocs_patch.models import (
    UNSET,
    Body,
    Bullet,
    BulletPreset,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Equation,
    ListDefinition,
    ListLevel,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Segment,
    Tab,
    Table,
    TableCell,
    TableCellStyle,
    TableColumn,
    TableRow,
    TabStop,
    TextRun,
    TextStyle,
)


def test_normalize_tree_normalizes_paragraph_text_styles_and_bullets() -> None:
    first_style = TextStyle(bold=True)
    final_style = TextStyle(italic=True)
    paragraph_style = ParagraphStyle(alignment="CENTER")
    bullet = BulletPreset(
        preset="BULLET_DISC_CIRCLE_SQUARE",
        nesting_level=2,
    )
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


def test_normalize_document_normalizes_every_loaded_tab_region() -> None:
    document = Document(
        document_id="document-1",
        title="Document",
        tabs=[
            Tab(
                tab_id="root",
                title="Root",
                index=0,
                content=DocumentTab(
                    body=Body(
                        content=[Paragraph(elements=[TextRun(content="Root\n")])]
                    ),
                    headers={
                        "header-1": Segment(
                            segment_id="header-1",
                            content=[Paragraph(elements=[TextRun(content="H\n")])],
                        )
                    },
                    footers={
                        "footer-1": Segment(
                            segment_id="footer-1",
                            content=[Paragraph(elements=[TextRun(content="F\n")])],
                        )
                    },
                    footnotes={
                        "footnote-1": Segment(
                            segment_id="footnote-1",
                            content=[
                                Paragraph(
                                    elements=[
                                        TextRun(content="N"),
                                        Equation(),
                                        TextRun(content="\n"),
                                    ]
                                )
                            ],
                        )
                    },
                ),
                children=[
                    Tab(
                        tab_id="child",
                        title="Child",
                        index=0,
                        content=DocumentTab(
                            body=Body(
                                content=[
                                    Paragraph(elements=[TextRun(content="Child\n")])
                                ]
                            )
                        ),
                        children=[],
                    )
                ],
            ),
            Tab(
                tab_id="unloaded",
                title="Unloaded",
                index=1,
                children=[],
            ),
        ],
    )

    content = normalize_document(document)

    assert content == DocumentContent(
        tabs={
            "root": TabContent(
                body=ContentStream(
                    items=[
                        TextUnit(content="R"),
                        TextUnit(content="o"),
                        TextUnit(content="o"),
                        TextUnit(content="t"),
                        ParagraphBoundary(),
                    ]
                ),
                headers={
                    "header-1": ContentStream(
                        items=[TextUnit(content="H"), ParagraphBoundary()]
                    )
                },
                footers={
                    "footer-1": ContentStream(
                        items=[TextUnit(content="F"), ParagraphBoundary()]
                    )
                },
                footnotes={
                    "footnote-1": ContentStream(
                        items=[
                            TextUnit(content="N"),
                            EquationUnit(),
                            ParagraphBoundary(),
                        ]
                    )
                },
            ),
            "child": TabContent(
                body=ContentStream(
                    items=[
                        TextUnit(content="C"),
                        TextUnit(content="h"),
                        TextUnit(content="i"),
                        TextUnit(content="l"),
                        TextUnit(content="d"),
                        ParagraphBoundary(),
                    ]
                ),
                headers={},
                footers={},
                footnotes={},
            ),
        }
    )


def test_compile_document_lowers_every_supported_edit_in_one_batch() -> None:
    source = Document(
        document_id="document-stress",
        title="Stress",
        revision_id="revision-stress",
        tabs=[
            Tab(
                tab_id="tab-stress",
                title="Stress tab",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(elements=[TextRun(content="a\n")]),
                            Paragraph(elements=[TextRun(content="cd\n")]),
                            Paragraph(elements=[TextRun(content="e\n")]),
                            Paragraph(
                                elements=[
                                    TextRun(
                                        content="f\n",
                                        text_style=TextStyle(italic=True),
                                    )
                                ]
                            ),
                            Paragraph(
                                elements=[TextRun(content="g\n")],
                                style=ParagraphStyle(alignment="START"),
                            ),
                            Paragraph(
                                elements=[TextRun(content="h\n")],
                                style=ParagraphStyle(
                                    heading_id="source-heading",
                                    tab_stops=[
                                        TabStop(
                                            offset=Dimension(magnitude=12, unit="PT"),
                                            alignment="START",
                                        )
                                    ],
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="i\n")],
                                bullet=Bullet(list_id="list-existing"),
                            ),
                            Paragraph(elements=[TextRun(content="j\n")]),
                            Paragraph(elements=[TextRun(content="k\n")]),
                            Paragraph(elements=[]),
                            Table(
                                table_key="table-grow",
                                column_styles=[
                                    TableColumn(width_type="EVENLY_DISTRIBUTED"),
                                    TableColumn(width_type="EVENLY_DISTRIBUTED"),
                                ],
                                rows=[
                                    TableRow(
                                        row_key="grow-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="grow-a-a",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="A\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-a-b",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="B\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="grow-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="grow-b-a",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="D\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-b-b",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="E\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Table(
                                table_key="table-shrink",
                                rows=[
                                    TableRow(
                                        row_key="shrink-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="shrink-a-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-a-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-a-c",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="shrink-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="shrink-b-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-b-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-b-c",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="shrink-row-c",
                                        cells=[
                                            TableCell(
                                                cell_key="shrink-c-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-c-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-c-c",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Table(
                                table_key="table-merge",
                                rows=[
                                    TableRow(
                                        row_key="merge-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="merge-head",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="merge-a-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="merge-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="merge-b-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="merge-b-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Table(
                                table_key="table-unmerge",
                                rows=[
                                    TableRow(
                                        row_key="unmerge-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="unmerge-head",
                                                content=[Paragraph(elements=[])],
                                                style=TableCellStyle(
                                                    row_span=2,
                                                    column_span=2,
                                                ),
                                            )
                                        ],
                                    ),
                                    TableRow(row_key="unmerge-row-b", cells=[]),
                                ],
                            ),
                        ]
                    ),
                    headers={
                        "header-stress": Segment(
                            segment_id="header-stress",
                            content=[Paragraph(elements=[TextRun(content="H\n")])],
                        )
                    },
                    footers={
                        "footer-stress": Segment(
                            segment_id="footer-stress",
                            content=[Paragraph(elements=[TextRun(content="FY\n")])],
                        )
                    },
                    footnotes={
                        "footnote-stress": Segment(
                            segment_id="footnote-stress",
                            content=[Paragraph(elements=[TextRun(content="N\n")])],
                        )
                    },
                ),
            )
        ],
    )
    target = Document(
        document_id="document-stress",
        title="Stress",
        tabs=[
            Tab(
                tab_id="tab-stress",
                title="Stress tab",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(elements=[TextRun(content="ab\n")]),
                            Paragraph(elements=[TextRun(content="c\n")]),
                            Paragraph(
                                elements=[
                                    TextRun(
                                        content="e\n",
                                        text_style=TextStyle(bold=True),
                                    )
                                ]
                            ),
                            Paragraph(elements=[TextRun(content="f\n")]),
                            Paragraph(
                                elements=[TextRun(content="g\n")],
                                style=ParagraphStyle(alignment="CENTER"),
                            ),
                            Paragraph(
                                elements=[TextRun(content="h\n")],
                                style=ParagraphStyle(
                                    heading_id="target-heading",
                                    tab_stops=[
                                        TabStop(
                                            offset=Dimension(magnitude=24, unit="PT"),
                                            alignment="END",
                                        )
                                    ],
                                ),
                            ),
                            Paragraph(elements=[TextRun(content="i\n")]),
                            Paragraph(
                                elements=[TextRun(content="j\n")],
                                bullet=BulletPreset(
                                    preset="BULLET_DISC_CIRCLE_SQUARE",
                                    nesting_level=0,
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="k\n")],
                                bullet=BulletPreset(
                                    preset="NUMBERED_DECIMAL_NESTED",
                                    nesting_level=2,
                                ),
                            ),
                            Table(
                                table_key="table-new",
                                rows=[
                                    TableRow(
                                        row_key="new-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="new-a-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="new-a-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="new-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="new-b-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="new-b-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Paragraph(elements=[]),
                            Table(
                                table_key="table-grow",
                                column_styles=[
                                    TableColumn(
                                        width_type="FIXED_WIDTH",
                                        width=Dimension(magnitude=10, unit="PT"),
                                    ),
                                    TableColumn(
                                        width_type="FIXED_WIDTH",
                                        width=Dimension(magnitude=20, unit="PT"),
                                    ),
                                    TableColumn(
                                        width_type="FIXED_WIDTH",
                                        width=Dimension(magnitude=30, unit="PT"),
                                    ),
                                ],
                                rows=[
                                    TableRow(
                                        row_key="grow-row-a",
                                        min_height=Dimension(magnitude=5, unit="PT"),
                                        prevent_overflow=True,
                                        cells=[
                                            TableCell(
                                                cell_key="grow-a-a",
                                                style=TableCellStyle(
                                                    background_color=Color(
                                                        red=0.1,
                                                        green=0.2,
                                                        blue=0.3,
                                                    )
                                                ),
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="A\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-a-b",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="B\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-a-c",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="C\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="grow-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="grow-b-a",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="D\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-b-b",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="E\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-b-c",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="F\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="grow-row-c",
                                        cells=[
                                            TableCell(
                                                cell_key="grow-c-a",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="G\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-c-b",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="H\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                            TableCell(
                                                cell_key="grow-c-c",
                                                content=[
                                                    Paragraph(
                                                        elements=[
                                                            TextRun(content="I\n")
                                                        ]
                                                    )
                                                ],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Table(
                                table_key="table-shrink",
                                rows=[
                                    TableRow(
                                        row_key="shrink-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="shrink-a-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-a-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="shrink-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="shrink-b-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="shrink-b-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            Table(
                                table_key="table-merge",
                                rows=[
                                    TableRow(
                                        row_key="merge-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="merge-head",
                                                content=[Paragraph(elements=[])],
                                                style=TableCellStyle(
                                                    row_span=2,
                                                    column_span=2,
                                                ),
                                            )
                                        ],
                                    ),
                                    TableRow(row_key="merge-row-b", cells=[]),
                                ],
                            ),
                            Table(
                                table_key="table-unmerge",
                                rows=[
                                    TableRow(
                                        row_key="unmerge-row-a",
                                        cells=[
                                            TableCell(
                                                cell_key="unmerge-head",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="unmerge-a-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                    TableRow(
                                        row_key="unmerge-row-b",
                                        cells=[
                                            TableCell(
                                                cell_key="unmerge-b-a",
                                                content=[Paragraph(elements=[])],
                                            ),
                                            TableCell(
                                                cell_key="unmerge-b-b",
                                                content=[Paragraph(elements=[])],
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ]
                    ),
                    headers={
                        "header-stress": Segment(
                            segment_id="header-stress",
                            content=[Paragraph(elements=[TextRun(content="HX\n")])],
                        )
                    },
                    footers={
                        "footer-stress": Segment(
                            segment_id="footer-stress",
                            content=[Paragraph(elements=[TextRun(content="F\n")])],
                        )
                    },
                    footnotes={
                        "footnote-stress": Segment(
                            segment_id="footnote-stress",
                            content=[Paragraph(elements=[TextRun(content="NO\n")])],
                        )
                    },
                ),
            )
        ],
    )

    assert compile_document(source=source, target=target) == {
        "requests": [
            {
                "insertTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                        "rowIndex": 1,
                        "columnIndex": 0,
                    },
                    "insertBelow": True,
                }
            },
            {
                "insertTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                        "rowIndex": 0,
                        "columnIndex": 1,
                    },
                    "insertRight": True,
                }
            },
            {
                "insertText": {
                    "location": {"index": 50, "tabId": "tab-stress"},
                    "text": "I",
                }
            },
            {
                "insertText": {
                    "location": {"index": 47, "tabId": "tab-stress"},
                    "text": "H",
                }
            },
            {
                "insertText": {
                    "location": {"index": 44, "tabId": "tab-stress"},
                    "text": "G",
                }
            },
            {
                "insertText": {
                    "location": {"index": 40, "tabId": "tab-stress"},
                    "text": "F",
                }
            },
            {
                "insertText": {
                    "location": {"index": 30, "tabId": "tab-stress"},
                    "text": "C",
                }
            },
            {
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                    "columnIndices": [0],
                    "tableColumnProperties": {
                        "widthType": "FIXED_WIDTH",
                        "width": {"magnitude": 10, "unit": "PT"},
                    },
                    "fields": "widthType,width",
                }
            },
            {
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                    "columnIndices": [1],
                    "tableColumnProperties": {
                        "widthType": "FIXED_WIDTH",
                        "width": {"magnitude": 20, "unit": "PT"},
                    },
                    "fields": "widthType,width",
                }
            },
            {
                "updateTableColumnProperties": {
                    "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                    "columnIndices": [2],
                    "tableColumnProperties": {
                        "widthType": "FIXED_WIDTH",
                        "width": {"magnitude": 30, "unit": "PT"},
                    },
                    "fields": "widthType,width",
                }
            },
            {
                "updateTableRowStyle": {
                    "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                    "rowIndices": [0],
                    "tableRowStyle": {
                        "minRowHeight": {"magnitude": 5, "unit": "PT"},
                        "preventOverflow": True,
                    },
                    "fields": "minRowHeight,preventOverflow,tableHeader",
                }
            },
            {
                "updateTableCellStyle": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": 21, "tabId": "tab-stress"},
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": 1,
                        "columnSpan": 1,
                    },
                    "tableCellStyle": {
                        "backgroundColor": {
                            "color": {
                                "rgbColor": {"red": 0.1, "green": 0.2, "blue": 0.3}
                            }
                        }
                    },
                    "fields": "backgroundColor,borderLeft,borderRight,borderTop,borderBottom,paddingLeft,paddingRight,paddingTop,paddingBottom,contentAlignment",
                }
            },
            {
                "deleteTableRow": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": 37, "tabId": "tab-stress"},
                        "rowIndex": 2,
                        "columnIndex": 0,
                    }
                }
            },
            {
                "deleteTableColumn": {
                    "tableCellLocation": {
                        "tableStartLocation": {"index": 37, "tabId": "tab-stress"},
                        "rowIndex": 0,
                        "columnIndex": 2,
                    }
                }
            },
            {
                "mergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": 60, "tabId": "tab-stress"},
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": 2,
                        "columnSpan": 2,
                    }
                }
            },
            {
                "unmergeTableCells": {
                    "tableRange": {
                        "tableCellLocation": {
                            "tableStartLocation": {"index": 72, "tabId": "tab-stress"},
                            "rowIndex": 0,
                            "columnIndex": 0,
                        },
                        "rowSpan": 2,
                        "columnSpan": 2,
                    }
                }
            },
            {
                "insertTable": {
                    "rows": 2,
                    "columns": 2,
                    "location": {"index": 19, "tabId": "tab-stress"},
                }
            },
            {
                "deleteContentRange": {
                    "range": {"startIndex": 4, "endIndex": 5, "tabId": "tab-stress"}
                }
            },
            {
                "insertText": {
                    "location": {"index": 2, "tabId": "tab-stress"},
                    "text": "b",
                }
            },
            {
                "deleteParagraphBullets": {
                    "range": {"startIndex": 14, "endIndex": 16, "tabId": "tab-stress"}
                }
            },
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": 16, "endIndex": 18, "tabId": "tab-stress"},
                    "paragraphStyle": {},
                    "fields": "indentStart,indentFirstLine",
                }
            },
            {
                "createParagraphBullets": {
                    "range": {"startIndex": 16, "endIndex": 18, "tabId": "tab-stress"},
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            },
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": 18, "endIndex": 20, "tabId": "tab-stress"},
                    "paragraphStyle": {},
                    "fields": "indentStart,indentFirstLine",
                }
            },
            {
                "insertText": {
                    "location": {"index": 18, "tabId": "tab-stress"},
                    "text": "\t\t",
                }
            },
            {
                "createParagraphBullets": {
                    "range": {"startIndex": 18, "endIndex": 22, "tabId": "tab-stress"},
                    "bulletPreset": "NUMBERED_DECIMAL_NESTED",
                }
            },
            {
                "updateParagraphStyle": {
                    "range": {"startIndex": 10, "endIndex": 12, "tabId": "tab-stress"},
                    "paragraphStyle": {"alignment": "CENTER"},
                    "fields": "namedStyleType,alignment,direction,lineSpacing,spacingMode,spaceAbove,spaceBelow,indentFirstLine,indentStart,indentEnd,keepLinesTogether,keepWithNext,avoidWidowAndOrphan,pageBreakBefore,borderBetween,borderTop,borderBottom,borderLeft,borderRight,shading",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 50, "endIndex": 51, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 47, "endIndex": 48, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 44, "endIndex": 45, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 40, "endIndex": 41, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 30, "endIndex": 31, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 2, "endIndex": 3, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 6, "endIndex": 8, "tabId": "tab-stress"},
                    "textStyle": {"bold": True},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": 8, "endIndex": 10, "tabId": "tab-stress"},
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "insertText": {
                    "location": {
                        "index": 1,
                        "tabId": "tab-stress",
                        "segmentId": "header-stress",
                    },
                    "text": "X",
                }
            },
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 2,
                        "tabId": "tab-stress",
                        "segmentId": "header-stress",
                    },
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
            {
                "deleteContentRange": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 2,
                        "tabId": "tab-stress",
                        "segmentId": "footer-stress",
                    }
                }
            },
            {
                "insertText": {
                    "location": {
                        "index": 1,
                        "tabId": "tab-stress",
                        "segmentId": "footnote-stress",
                    },
                    "text": "O",
                }
            },
            {
                "updateTextStyle": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 2,
                        "tabId": "tab-stress",
                        "segmentId": "footnote-stress",
                    },
                    "textStyle": {},
                    "fields": "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,weightedFontFamily,foregroundColor,backgroundColor,link",
                }
            },
        ],
        "writeControl": {"requiredRevisionId": "revision-stress"},
    }


def test_compile_document_normalizes_custom_bullets_only_when_enabled() -> None:
    custom_list = ListDefinition(
        levels=[
            ListLevel(glyph_symbol="●", glyph_format="%0"),
            ListLevel(glyph_symbol="⇑", glyph_format="%1"),
            ListLevel(glyph_symbol="■", glyph_format="%2"),
            ListLevel(glyph_symbol="●", glyph_format="%3"),
            ListLevel(glyph_symbol="○", glyph_format="%4"),
            ListLevel(glyph_symbol="■", glyph_format="%5"),
            ListLevel(glyph_symbol="●", glyph_format="%6"),
            ListLevel(glyph_symbol="○", glyph_format="%7"),
            ListLevel(glyph_symbol="■", glyph_format="%8"),
        ]
    )
    source = Document(
        document_id="document-custom-list",
        title="Custom list",
        revision_id="revision-custom-list",
        tabs=[
            Tab(
                tab_id="tab-custom-list",
                title="Custom list",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                elements=[TextRun(content="A\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=0,
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="B\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=1,
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="C\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=0,
                                ),
                            ),
                        ]
                    ),
                    lists={"list-custom": custom_list},
                ),
            )
        ],
    )
    target = Document(
        document_id="document-custom-list",
        title="Custom list",
        tabs=[
            Tab(
                tab_id="tab-custom-list",
                title="Custom list",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                elements=[TextRun(content="A\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=0,
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="B\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=1,
                                ),
                            ),
                            Paragraph(
                                elements=[TextRun(content="C\n")],
                                bullet=Bullet(
                                    list_id="list-custom",
                                    nesting_level=1,
                                ),
                            ),
                        ]
                    ),
                    lists={"list-custom": custom_list},
                ),
            )
        ],
    )

    with pytest.raises(
        UnsupportedTransformation,
        match="customized bullet list",
    ):
        compile_document(source=source, target=target)

    assert compile_document(
        source=source,
        target=target,
        allow_bullet_normalization=True,
    ) == {
        "requests": [
            {
                "deleteParagraphBullets": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 7,
                        "tabId": "tab-custom-list",
                    }
                }
            },
            {
                "updateParagraphStyle": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 7,
                        "tabId": "tab-custom-list",
                    },
                    "paragraphStyle": {},
                    "fields": "indentStart,indentFirstLine",
                }
            },
            {
                "insertText": {
                    "location": {
                        "index": 5,
                        "tabId": "tab-custom-list",
                    },
                    "text": "\t",
                }
            },
            {
                "insertText": {
                    "location": {
                        "index": 3,
                        "tabId": "tab-custom-list",
                    },
                    "text": "\t",
                }
            },
            {
                "createParagraphBullets": {
                    "range": {
                        "startIndex": 1,
                        "endIndex": 9,
                        "tabId": "tab-custom-list",
                    },
                    "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                }
            },
        ],
        "writeControl": {"requiredRevisionId": "revision-custom-list"},
    }
