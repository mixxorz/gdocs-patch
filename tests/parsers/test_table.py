from gdocs_patch.models import UNSET, Paragraph
from gdocs_patch.parsers.table import (
    table_cell_border_parser,
    table_cell_parser,
    table_cell_style_parser,
    table_column_parser,
    table_parser,
    table_row_parser,
)


def test_table_cell_border_maps_color_width_and_dash_style() -> None:
    border = table_cell_border_parser.parse(
        {
            "color": {"color": {"rgbColor": {"red": 0.25}}},
            "width": {"magnitude": 2, "unit": "PT"},
            "dashStyle": "DASH",
        }
    )

    assert border.color is not None
    assert border.color.red == 0.25
    assert border.width.magnitude == 2
    assert border.width.unit == "PT"
    assert border.dash_style == "DASH"


def test_table_cell_style_maps_all_supported_properties() -> None:
    style = table_cell_style_parser.parse(
        {
            "rowSpan": 2,
            "columnSpan": 3,
            "backgroundColor": {},
            "borderLeft": _border("SOLID", 1),
            "borderRight": _border("DOT", 2),
            "borderTop": _border("DASH", 3),
            "borderBottom": _border("DASH_STYLE_UNSPECIFIED", 4),
            "paddingLeft": _dimension(5),
            "paddingRight": _dimension(6),
            "paddingTop": _dimension(7),
            "paddingBottom": _dimension(8),
            "contentAlignment": "MIDDLE",
        }
    )

    assert style.row_span == 2
    assert style.column_span == 3
    assert style.background_color is None
    assert style.border_left.dash_style == "SOLID"
    assert style.border_right.dash_style == "DOT"
    assert style.border_top.dash_style == "DASH"
    assert style.border_bottom.width.magnitude == 4
    assert style.padding_left.magnitude == 5
    assert style.padding_right.magnitude == 6
    assert style.padding_top.magnitude == 7
    assert style.padding_bottom.magnitude == 8
    assert style.content_alignment == "MIDDLE"


def test_table_cell_recursively_maps_paragraph_and_ignores_indices() -> None:
    cell = table_cell_parser.parse(
        {
            "startIndex": 10,
            "endIndex": 20,
            "content": [
                {
                    "startIndex": 11,
                    "endIndex": 19,
                    "paragraph": {"elements": [{"textRun": {"content": "cell"}}]},
                }
            ],
            "tableCellStyle": {"rowSpan": 2},
            "suggestedInsertionIds": ["ignored"],
            "suggestedDeletionIds": ["ignored"],
        }
    )

    assert len(cell.content) == 1
    assert isinstance(cell.content[0], Paragraph)
    assert cell.content[0].elements[0].content == "cell"
    assert cell.style.row_span == 2


def test_table_row_maps_cells_and_complete_style_while_ignoring_indices() -> None:
    row = table_row_parser.parse(
        {
            "startIndex": 1,
            "endIndex": 9,
            "tableCells": [{}, {}],
            "tableRowStyle": {
                "minRowHeight": _dimension(12),
                "preventOverflow": True,
                "tableHeader": False,
            },
            "suggestedInsertionIds": ["ignored"],
            "suggestedDeletionIds": ["ignored"],
        }
    )

    assert len(row.cells) == 2
    assert row.min_height.magnitude == 12
    assert row.prevent_overflow is True
    assert row.is_header is False


def test_table_column_maps_fixed_width() -> None:
    column = table_column_parser.parse(
        {"widthType": "FIXED_WIDTH", "width": _dimension(72)}
    )

    assert column.width_type == "FIXED_WIDTH"
    assert column.width.magnitude == 72
    assert column.width.unit == "PT"


def test_table_maps_rows_and_column_styles_while_ignoring_counts() -> None:
    table = table_parser.parse(
        {
            "rows": 99,
            "columns": 88,
            "tableRows": [{"tableCells": [{}]}],
            "tableStyle": {
                "tableColumnProperties": [
                    {"widthType": "FIXED_WIDTH", "width": _dimension(100)},
                    {"widthType": "EVENLY_DISTRIBUTED"},
                ]
            },
        }
    )

    assert len(table.rows) == 1
    assert len(table.rows[0].cells) == 1
    assert table.column_styles is not UNSET
    assert [column.width_type for column in table.column_styles] == [
        "FIXED_WIDTH",
        "EVENLY_DISTRIBUTED",
    ]


def _dimension(magnitude: float) -> dict[str, object]:
    return {"magnitude": magnitude, "unit": "PT"}


def _border(dash_style: str, magnitude: float) -> dict[str, object]:
    return {
        "color": {},
        "width": _dimension(magnitude),
        "dashStyle": dash_style,
    }
