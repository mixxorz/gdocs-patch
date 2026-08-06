from gdocs_patch.compiler.edit_script import (
    ApplyParagraphStyle,
    ApplyTableCellStyle,
    ApplyTableColumnProperties,
    ApplyTableRowStyle,
    ApplyTextStyle,
    CreateParagraphBullets,
    DeleteContent,
    DeleteParagraphBullets,
    DeleteTableColumn,
    DeleteTableRow,
    EditScript,
    InsertTable,
    InsertTableColumn,
    InsertTableRow,
    InsertText,
    MergeTableCells,
    UnmergeTableCells,
)
from gdocs_patch.compiler.lowering import lower_edit_script
from gdocs_patch.models import (
    UNSET,
    BookmarkLink,
    BulletPreset,
    Color,
    Dimension,
    ParagraphBorder,
    ParagraphStyle,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TabStop,
    TextStyle,
)


def test_lowers_content_paragraph_and_bullet_edits() -> None:
    edit_script = EditScript(
        edits=[
            InsertText(index=4, text="new"),
            DeleteContent(start_index=8, end_index=11),
            ApplyTextStyle(
                start_index=1,
                end_index=4,
                text_style=TextStyle(
                    bold=True,
                    italic=False,
                    font_size=Dimension(magnitude=12, unit="PT"),
                    font_family="Roboto",
                    font_weight=500,
                    foreground_color=Color(red=0.1, green=0.2, blue=0.3),
                    background_color=None,
                    link=BookmarkLink(
                        bookmark_id="bookmark-1",
                        tab_id="tab-linked",
                    ),
                ),
            ),
            ApplyTextStyle(start_index=4, end_index=5, text_style=UNSET),
            ApplyParagraphStyle(
                start_index=0,
                end_index=12,
                paragraph_style=ParagraphStyle(
                    named_style_type="HEADING_2",
                    alignment="CENTER",
                    space_above=Dimension(magnitude=6, unit="PT"),
                    border_bottom=ParagraphBorder(
                        color=Color(red=0.4, green=0.5, blue=0.6),
                        width=Dimension(magnitude=1, unit="PT"),
                        padding=Dimension(magnitude=2, unit="PT"),
                        dash_style="SOLID",
                    ),
                    shading_color=None,
                    heading_id="read-only-heading",
                    tab_stops=[
                        TabStop(
                            offset=Dimension(magnitude=36, unit="PT"),
                            alignment="START",
                        )
                    ],
                ),
            ),
            ApplyParagraphStyle(
                start_index=12,
                end_index=13,
                paragraph_style=UNSET,
            ),
            CreateParagraphBullets(
                start_index=13,
                end_index=20,
                bullet_preset=BulletPreset(
                    preset="BULLET_DISC_CIRCLE_SQUARE",
                    nesting_level=2,
                ),
            ),
            DeleteParagraphBullets(start_index=20, end_index=27),
        ]
    )

    assert lower_edit_script(edit_script=edit_script, tab_id="tab-1") == [
        {
            "insertText": {
                "location": {"index": 4, "tabId": "tab-1"},
                "text": "new",
            }
        },
        {
            "deleteContentRange": {
                "range": {
                    "startIndex": 8,
                    "endIndex": 11,
                    "tabId": "tab-1",
                }
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": 1,
                    "endIndex": 4,
                    "tabId": "tab-1",
                },
                "textStyle": {
                    "bold": True,
                    "italic": False,
                    "fontSize": {"magnitude": 12, "unit": "PT"},
                    "weightedFontFamily": {
                        "fontFamily": "Roboto",
                        "weight": 500,
                    },
                    "foregroundColor": {
                        "color": {"rgbColor": {"red": 0.1, "green": 0.2, "blue": 0.3}}
                    },
                    "backgroundColor": {},
                    "link": {
                        "bookmarkId": "bookmark-1",
                        "tabId": "tab-linked",
                    },
                },
                "fields": (
                    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,"
                    "fontSize,weightedFontFamily,foregroundColor,backgroundColor,link"
                ),
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": 4,
                    "endIndex": 5,
                    "tabId": "tab-1",
                },
                "textStyle": {},
                "fields": (
                    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,"
                    "fontSize,weightedFontFamily,foregroundColor,backgroundColor,link"
                ),
            }
        },
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": 0,
                    "endIndex": 12,
                    "tabId": "tab-1",
                },
                "paragraphStyle": {
                    "namedStyleType": "HEADING_2",
                    "alignment": "CENTER",
                    "spaceAbove": {"magnitude": 6, "unit": "PT"},
                    "borderBottom": {
                        "color": {
                            "color": {
                                "rgbColor": {
                                    "red": 0.4,
                                    "green": 0.5,
                                    "blue": 0.6,
                                }
                            }
                        },
                        "width": {"magnitude": 1, "unit": "PT"},
                        "padding": {"magnitude": 2, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                    "shading": {"backgroundColor": {}},
                },
                "fields": (
                    "namedStyleType,alignment,direction,lineSpacing,spacingMode,"
                    "spaceAbove,spaceBelow,indentFirstLine,indentStart,indentEnd,"
                    "keepLinesTogether,keepWithNext,avoidWidowAndOrphan,"
                    "pageBreakBefore,borderBetween,borderTop,borderBottom,borderLeft,"
                    "borderRight,shading"
                ),
            }
        },
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": 12,
                    "endIndex": 13,
                    "tabId": "tab-1",
                },
                "paragraphStyle": {},
                "fields": (
                    "namedStyleType,alignment,direction,lineSpacing,spacingMode,"
                    "spaceAbove,spaceBelow,indentFirstLine,indentStart,indentEnd,"
                    "keepLinesTogether,keepWithNext,avoidWidowAndOrphan,"
                    "pageBreakBefore,borderBetween,borderTop,borderBottom,borderLeft,"
                    "borderRight,shading"
                ),
            }
        },
        {
            "insertText": {
                "location": {"index": 13, "tabId": "tab-1"},
                "text": "\t\t",
            }
        },
        {
            "createParagraphBullets": {
                "range": {
                    "startIndex": 13,
                    "endIndex": 22,
                    "tabId": "tab-1",
                },
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        },
        {
            "deleteParagraphBullets": {
                "range": {
                    "startIndex": 20,
                    "endIndex": 27,
                    "tabId": "tab-1",
                }
            }
        },
    ]


def test_lowers_all_table_edits() -> None:
    edit_script = EditScript(
        edits=[
            InsertTable(index=10, rows=2, columns=3),
            InsertTableRow(
                table_start_index=10,
                row_index=0,
                column_index=1,
                insert_below=True,
            ),
            InsertTableColumn(
                table_start_index=10,
                row_index=1,
                column_index=0,
                insert_right=False,
            ),
            DeleteTableRow(table_start_index=10, row_index=2, column_index=1),
            DeleteTableColumn(table_start_index=10, row_index=0, column_index=2),
            MergeTableCells(
                table_start_index=10,
                row_index=0,
                column_index=0,
                row_span=2,
                column_span=2,
            ),
            UnmergeTableCells(
                table_start_index=10,
                row_index=1,
                column_index=1,
                row_span=2,
                column_span=2,
            ),
            ApplyTableColumnProperties(
                table_start_index=10,
                column_index=1,
                column_properties=TableColumn(
                    width_type="FIXED_WIDTH",
                    width=Dimension(magnitude=72, unit="PT"),
                ),
            ),
            ApplyTableColumnProperties(
                table_start_index=10,
                column_index=2,
                column_properties=UNSET,
            ),
            ApplyTableRowStyle(
                table_start_index=10,
                row_index=0,
                min_height=Dimension(magnitude=24, unit="PT"),
                prevent_overflow=True,
                is_header=False,
            ),
            ApplyTableCellStyle(
                table_start_index=10,
                row_index=0,
                column_index=0,
                row_span=2,
                column_span=2,
                cell_style=TableCellStyle(
                    row_span=2,
                    column_span=2,
                    background_color=Color(red=0.7, green=0.8, blue=0.9),
                    border_left=TableCellBorder(
                        color=Color(red=0.1, green=0.2, blue=0.3),
                        width=Dimension(magnitude=1, unit="PT"),
                        dash_style="DASH",
                    ),
                    padding_top=Dimension(magnitude=4, unit="PT"),
                    content_alignment="MIDDLE",
                ),
            ),
            ApplyTableCellStyle(
                table_start_index=10,
                row_index=2,
                column_index=2,
                row_span=1,
                column_span=1,
                cell_style=UNSET,
            ),
        ]
    )
    assert lower_edit_script(
        edit_script=edit_script,
        tab_id="tab-table",
        segment_id="footer-1",
    ) == [
        {
            "insertTable": {
                "rows": 2,
                "columns": 3,
                "location": {"index": 9, "tabId": "tab-table", "segmentId": "footer-1"},
            }
        },
        {
            "insertTableRow": {
                "tableCellLocation": {
                    "tableStartLocation": {
                        "index": 10,
                        "tabId": "tab-table",
                        "segmentId": "footer-1",
                    },
                    "rowIndex": 0,
                    "columnIndex": 1,
                },
                "insertBelow": True,
            }
        },
        {
            "insertTableColumn": {
                "tableCellLocation": {
                    "tableStartLocation": {
                        "index": 10,
                        "tabId": "tab-table",
                        "segmentId": "footer-1",
                    },
                    "rowIndex": 1,
                    "columnIndex": 0,
                },
                "insertRight": False,
            }
        },
        {
            "deleteTableRow": {
                "tableCellLocation": {
                    "tableStartLocation": {
                        "index": 10,
                        "tabId": "tab-table",
                        "segmentId": "footer-1",
                    },
                    "rowIndex": 2,
                    "columnIndex": 1,
                }
            }
        },
        {
            "deleteTableColumn": {
                "tableCellLocation": {
                    "tableStartLocation": {
                        "index": 10,
                        "tabId": "tab-table",
                        "segmentId": "footer-1",
                    },
                    "rowIndex": 0,
                    "columnIndex": 2,
                }
            }
        },
        {
            "mergeTableCells": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {
                            "index": 10,
                            "tabId": "tab-table",
                            "segmentId": "footer-1",
                        },
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
                        "tableStartLocation": {
                            "index": 10,
                            "tabId": "tab-table",
                            "segmentId": "footer-1",
                        },
                        "rowIndex": 1,
                        "columnIndex": 1,
                    },
                    "rowSpan": 2,
                    "columnSpan": 2,
                }
            }
        },
        {
            "updateTableColumnProperties": {
                "tableStartLocation": {
                    "index": 10,
                    "tabId": "tab-table",
                    "segmentId": "footer-1",
                },
                "columnIndices": [1],
                "tableColumnProperties": {
                    "widthType": "FIXED_WIDTH",
                    "width": {"magnitude": 72, "unit": "PT"},
                },
                "fields": "widthType,width",
            }
        },
        {
            "updateTableColumnProperties": {
                "tableStartLocation": {
                    "index": 10,
                    "tabId": "tab-table",
                    "segmentId": "footer-1",
                },
                "columnIndices": [2],
                "tableColumnProperties": {},
                "fields": "widthType,width",
            }
        },
        {
            "updateTableRowStyle": {
                "tableStartLocation": {
                    "index": 10,
                    "tabId": "tab-table",
                    "segmentId": "footer-1",
                },
                "rowIndices": [0],
                "tableRowStyle": {
                    "minRowHeight": {"magnitude": 24, "unit": "PT"},
                    "preventOverflow": True,
                    "tableHeader": False,
                },
                "fields": "minRowHeight,preventOverflow,tableHeader",
            }
        },
        {
            "updateTableCellStyle": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {
                            "index": 10,
                            "tabId": "tab-table",
                            "segmentId": "footer-1",
                        },
                        "rowIndex": 0,
                        "columnIndex": 0,
                    },
                    "rowSpan": 2,
                    "columnSpan": 2,
                },
                "tableCellStyle": {
                    "backgroundColor": {
                        "color": {"rgbColor": {"red": 0.7, "green": 0.8, "blue": 0.9}}
                    },
                    "borderLeft": {
                        "color": {
                            "color": {
                                "rgbColor": {"red": 0.1, "green": 0.2, "blue": 0.3}
                            }
                        },
                        "width": {"magnitude": 1, "unit": "PT"},
                        "dashStyle": "DASH",
                    },
                    "paddingTop": {"magnitude": 4, "unit": "PT"},
                    "contentAlignment": "MIDDLE",
                },
                "fields": (
                    "backgroundColor,borderLeft,borderRight,borderTop,borderBottom,"
                    "paddingLeft,paddingRight,paddingTop,paddingBottom,contentAlignment"
                ),
            }
        },
        {
            "updateTableCellStyle": {
                "tableRange": {
                    "tableCellLocation": {
                        "tableStartLocation": {
                            "index": 10,
                            "tabId": "tab-table",
                            "segmentId": "footer-1",
                        },
                        "rowIndex": 2,
                        "columnIndex": 2,
                    },
                    "rowSpan": 1,
                    "columnSpan": 1,
                },
                "tableCellStyle": {},
                "fields": (
                    "backgroundColor,borderLeft,borderRight,borderTop,borderBottom,"
                    "paddingLeft,paddingRight,paddingTop,paddingBottom,contentAlignment"
                ),
            }
        },
    ]


def test_lowers_body_and_segment_locations() -> None:
    edit_script = EditScript(edits=[InsertText(index=3, text="header")])

    assert lower_edit_script(
        edit_script=edit_script,
        tab_id="tab-2",
        segment_id="header-1",
    ) == [
        {
            "insertText": {
                "location": {
                    "index": 3,
                    "tabId": "tab-2",
                    "segmentId": "header-1",
                },
                "text": "header",
            }
        }
    ]
    assert lower_edit_script(edit_script=edit_script, tab_id="tab-2") == [
        {
            "insertText": {
                "location": {
                    "index": 3,
                    "tabId": "tab-2",
                },
                "text": "header",
            }
        }
    ]
