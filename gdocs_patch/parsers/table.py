from typing import Literal, cast

from gdocs_patch.models.base import UNSET, Color, Dimension, UnsetType
from gdocs_patch.models.document import StructuralElement, TableOfContents
from gdocs_patch.models.paragraph import Paragraph
from gdocs_patch.models.section import SectionBreak
from gdocs_patch.models.table import (
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableRow,
)

from .base import (
    GDocParseError,
    GDocParser,
    JsonObject,
    JsonValue,
    array_value,
    field_path,
    index_path,
    integer_value,
    literal_value,
    object_value,
    optional_boolean_field,
    parse_optional_color,
    required_field,
)


class TableCellBorderParser(GDocParser[TableCellBorder]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableCellBorder:
        value = object_value(data, path)
        return TableCellBorder(
            color=parse_optional_color(
                required_field(value, "color", path), field_path(path, "color")
            ),
            width=Dimension.gdoc_parser.parse(
                required_field(value, "width", path), path=field_path(path, "width")
            ),
            dash_style=literal_value(
                required_field(value, "dashStyle", path),
                ("DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"),
                field_path(path, "dashStyle"),
            ),
        )


class TableCellStyleParser(GDocParser[TableCellStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableCellStyle:
        value = object_value(data, path)
        content_alignment: (
            Literal[
                "CONTENT_ALIGNMENT_UNSPECIFIED",
                "CONTENT_ALIGNMENT_UNSUPPORTED",
                "TOP",
                "MIDDLE",
                "BOTTOM",
            ]
            | UnsetType
        ) = (
            cast(
                Literal[
                    "CONTENT_ALIGNMENT_UNSPECIFIED",
                    "CONTENT_ALIGNMENT_UNSUPPORTED",
                    "TOP",
                    "MIDDLE",
                    "BOTTOM",
                ],
                literal_value(
                    value["contentAlignment"],
                    (
                        "CONTENT_ALIGNMENT_UNSPECIFIED",
                        "CONTENT_ALIGNMENT_UNSUPPORTED",
                        "TOP",
                        "MIDDLE",
                        "BOTTOM",
                    ),
                    field_path(path, "contentAlignment"),
                ),
            )
            if "contentAlignment" in value
            else UNSET
        )
        try:
            return TableCellStyle(
                row_span=(
                    integer_value(value["rowSpan"], field_path(path, "rowSpan"))
                    if "rowSpan" in value
                    else 1
                ),
                column_span=(
                    integer_value(value["columnSpan"], field_path(path, "columnSpan"))
                    if "columnSpan" in value
                    else 1
                ),
                background_color=self._optional_color(value, path),
                border_left=self._optional_border(value, "borderLeft", path),
                border_right=self._optional_border(value, "borderRight", path),
                border_top=self._optional_border(value, "borderTop", path),
                border_bottom=self._optional_border(value, "borderBottom", path),
                padding_left=self._optional_dimension(value, "paddingLeft", path),
                padding_right=self._optional_dimension(value, "paddingRight", path),
                padding_top=self._optional_dimension(value, "paddingTop", path),
                padding_bottom=self._optional_dimension(value, "paddingBottom", path),
                content_alignment=content_alignment,
            )
        except ValueError as error:
            if isinstance(error, GDocParseError):
                raise
            raise GDocParseError(path, str(error)) from error

    @staticmethod
    def _optional_color(value: JsonObject, path: str) -> Color | None | UnsetType:
        if "backgroundColor" not in value:
            return UNSET
        return parse_optional_color(
            value["backgroundColor"], field_path(path, "backgroundColor")
        )

    @staticmethod
    def _optional_border(
        value: JsonObject, key: str, path: str
    ) -> TableCellBorder | UnsetType:
        if key not in value:
            return UNSET
        return TableCellBorder.gdoc_parser.parse(value[key], path=field_path(path, key))

    @staticmethod
    def _optional_dimension(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return Dimension.gdoc_parser.parse(value[key], path=field_path(path, key))


class TableCellParser(GDocParser[TableCell]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableCell:
        value = object_value(data, path)
        content_path = field_path(path, "content")
        content = (
            array_value(value["content"], content_path) if "content" in value else []
        )
        parsed_content: list[StructuralElement] = []
        for index, item in enumerate(content):
            item_path = index_path(content_path, index)
            wrapper = object_value(item, item_path)
            keys = ("paragraph", "sectionBreak", "table", "tableOfContents")
            present = [key for key in keys if key in wrapper]
            if len(present) != 1:
                raise GDocParseError(
                    item_path, "expected exactly one supported structural element"
                )
            key = present[0]
            inner = wrapper[key]
            inner_path = field_path(item_path, key)
            if key == "paragraph":
                parsed_content.append(
                    Paragraph.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "sectionBreak":
                parsed_content.append(
                    SectionBreak.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "table":
                parsed_content.append(Table.gdoc_parser.parse(inner, path=inner_path))
            else:
                parsed_content.append(
                    TableOfContents.gdoc_parser.parse(inner, path=inner_path)
                )
        return TableCell(
            content=parsed_content,
            style=(
                TableCellStyle.gdoc_parser.parse(
                    value["tableCellStyle"], path=field_path(path, "tableCellStyle")
                )
                if "tableCellStyle" in value
                else UNSET
            ),
        )


class TableRowParser(GDocParser[TableRow]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableRow:
        value = object_value(data, path)
        cells_path = field_path(path, "tableCells")
        cells = (
            array_value(value["tableCells"], cells_path)
            if "tableCells" in value
            else []
        )
        style = (
            object_value(value["tableRowStyle"], field_path(path, "tableRowStyle"))
            if "tableRowStyle" in value
            else None
        )
        style_path = field_path(path, "tableRowStyle")
        return TableRow(
            cells=[
                TableCell.gdoc_parser.parse(cell, path=index_path(cells_path, index))
                for index, cell in enumerate(cells)
            ],
            min_height=(
                Dimension.gdoc_parser.parse(
                    style["minRowHeight"], path=field_path(style_path, "minRowHeight")
                )
                if style is not None and "minRowHeight" in style
                else UNSET
            ),
            prevent_overflow=(
                optional_boolean_field(style, "preventOverflow", style_path)
                if style is not None
                else UNSET
            ),
            is_header=(
                optional_boolean_field(style, "tableHeader", style_path)
                if style is not None
                else UNSET
            ),
        )


class TableColumnParser(GDocParser[TableColumn]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableColumn:
        value = object_value(data, path)
        try:
            return TableColumn(
                width_type=literal_value(
                    required_field(value, "widthType", path),
                    (
                        "WIDTH_TYPE_UNSPECIFIED",
                        "EVENLY_DISTRIBUTED",
                        "FIXED_WIDTH",
                    ),
                    field_path(path, "widthType"),
                ),
                width=(
                    Dimension.gdoc_parser.parse(
                        value["width"], path=field_path(path, "width")
                    )
                    if "width" in value
                    else UNSET
                ),
            )
        except ValueError as error:
            if isinstance(error, GDocParseError):
                raise
            raise GDocParseError(path, str(error)) from error


class TableParser(GDocParser[Table]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Table:
        value = object_value(data, path)
        rows_path = field_path(path, "tableRows")
        rows = (
            array_value(value["tableRows"], rows_path) if "tableRows" in value else []
        )
        if "tableStyle" not in value:
            column_styles: list[TableColumn] | UnsetType = UNSET
        else:
            style_path = field_path(path, "tableStyle")
            style = object_value(value["tableStyle"], style_path)
            columns_path = field_path(style_path, "tableColumnProperties")
            columns = (
                array_value(style["tableColumnProperties"], columns_path)
                if "tableColumnProperties" in style
                else []
            )
            column_styles = [
                TableColumn.gdoc_parser.parse(
                    column, path=index_path(columns_path, index)
                )
                for index, column in enumerate(columns)
            ]
        return Table(
            rows=[
                TableRow.gdoc_parser.parse(row, path=index_path(rows_path, index))
                for index, row in enumerate(rows)
            ],
            column_styles=column_styles,
        )


TableCellBorder.gdoc_parser = TableCellBorderParser()
TableCellStyle.gdoc_parser = TableCellStyleParser()
TableCell.gdoc_parser = TableCellParser()
TableRow.gdoc_parser = TableRowParser()
TableColumn.gdoc_parser = TableColumnParser()
Table.gdoc_parser = TableParser()
