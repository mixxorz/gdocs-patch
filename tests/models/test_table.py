import pytest

from gdocs_patch.models.base import Dimension
from gdocs_patch.models.table import TableCellStyle, TableColumn


def test_table_cell_style_defaults_spans_to_one() -> None:
    style = TableCellStyle()

    assert style.row_span == 1
    assert style.column_span == 1


@pytest.mark.parametrize(
    ("row_span", "column_span", "message"),
    [
        (0, 1, "row_span must be positive"),
        (1, 0, "column_span must be positive"),
        (-1, 1, "row_span must be positive"),
    ],
)
def test_table_cell_style_rejects_non_positive_spans(
    row_span: int,
    column_span: int,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        TableCellStyle(row_span=row_span, column_span=column_span)


def test_fixed_width_table_column_requires_width() -> None:
    with pytest.raises(
        ValueError,
        match="width must be set when width_type is FIXED_WIDTH",
    ):
        TableColumn(width_type="FIXED_WIDTH")


def test_non_fixed_table_column_rejects_width() -> None:
    with pytest.raises(
        ValueError,
        match="width must be unset unless width_type is FIXED_WIDTH",
    ):
        TableColumn(
            width_type="EVENLY_DISTRIBUTED",
            width=Dimension(magnitude=72, unit="PT"),
        )


def test_valid_fixed_width_table_column() -> None:
    width = Dimension(magnitude=72, unit="PT")

    column = TableColumn(width_type="FIXED_WIDTH", width=width)

    assert column.width is width
