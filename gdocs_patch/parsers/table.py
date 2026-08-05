from typing import Any

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

from .base import GDocParser, parse_optional_color


class TableCellBorderParser(GDocParser[TableCellBorder]):
    def parse(self, data: Any) -> TableCellBorder:
        return TableCellBorder(
            color=parse_optional_color(data["color"]),
            width=Dimension.gdoc_parser.parse(data["width"]),
            dash_style=data["dashStyle"],
        )


class TableCellStyleParser(GDocParser[TableCellStyle]):
    def parse(self, data: Any) -> TableCellStyle:
        return TableCellStyle(
            row_span=data.get("rowSpan", 1),
            column_span=data.get("columnSpan", 1),
            background_color=self._optional_color(data),
            border_left=self._optional_border(data, "borderLeft"),
            border_right=self._optional_border(data, "borderRight"),
            border_top=self._optional_border(data, "borderTop"),
            border_bottom=self._optional_border(data, "borderBottom"),
            padding_left=self._optional_dimension(data, "paddingLeft"),
            padding_right=self._optional_dimension(data, "paddingRight"),
            padding_top=self._optional_dimension(data, "paddingTop"),
            padding_bottom=self._optional_dimension(data, "paddingBottom"),
            content_alignment=data.get("contentAlignment", UNSET),
        )

    @staticmethod
    def _optional_color(data: Any) -> Color | None | UnsetType:
        if "backgroundColor" not in data:
            return UNSET
        return parse_optional_color(data["backgroundColor"])

    @staticmethod
    def _optional_border(data: Any, key: str) -> TableCellBorder | UnsetType:
        if key not in data:
            return UNSET
        return TableCellBorder.gdoc_parser.parse(data[key])

    @staticmethod
    def _optional_dimension(data: Any, key: str) -> Dimension | UnsetType:
        if key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])


class TableCellParser(GDocParser[TableCell]):
    def parse(self, data: Any) -> TableCell:
        parsed_content: list[StructuralElement] = []
        for wrapper in data.get("content", []):
            if "paragraph" in wrapper:
                parsed_content.append(Paragraph.gdoc_parser.parse(wrapper["paragraph"]))
            elif "sectionBreak" in wrapper:
                parsed_content.append(
                    SectionBreak.gdoc_parser.parse(wrapper["sectionBreak"])
                )
            elif "table" in wrapper:
                parsed_content.append(Table.gdoc_parser.parse(wrapper["table"]))
            else:
                parsed_content.append(
                    TableOfContents.gdoc_parser.parse(wrapper["tableOfContents"])
                )
        return TableCell(
            content=parsed_content,
            style=(
                TableCellStyle.gdoc_parser.parse(data["tableCellStyle"])
                if "tableCellStyle" in data
                else UNSET
            ),
        )


class TableRowParser(GDocParser[TableRow]):
    def parse(self, data: Any) -> TableRow:
        style = data.get("tableRowStyle", {})
        return TableRow(
            cells=[
                TableCell.gdoc_parser.parse(cell) for cell in data.get("tableCells", [])
            ],
            min_height=(
                Dimension.gdoc_parser.parse(style["minRowHeight"])
                if "minRowHeight" in style
                else UNSET
            ),
            prevent_overflow=style.get("preventOverflow", UNSET),
            is_header=style.get("tableHeader", UNSET),
        )


class TableColumnParser(GDocParser[TableColumn]):
    def parse(self, data: Any) -> TableColumn:
        return TableColumn(
            width_type=data["widthType"],
            width=(
                Dimension.gdoc_parser.parse(data["width"]) if "width" in data else UNSET
            ),
        )


class TableParser(GDocParser[Table]):
    def parse(self, data: Any) -> Table:
        if "tableStyle" not in data:
            column_styles: list[TableColumn] | UnsetType = UNSET
        else:
            column_styles = [
                TableColumn.gdoc_parser.parse(column)
                for column in data["tableStyle"].get("tableColumnProperties", [])
            ]
        return Table(
            rows=[TableRow.gdoc_parser.parse(row) for row in data.get("tableRows", [])],
            column_styles=column_styles,
        )


TableCellBorder.gdoc_parser = TableCellBorderParser()
TableCellStyle.gdoc_parser = TableCellStyleParser()
TableCell.gdoc_parser = TableCellParser()
TableRow.gdoc_parser = TableRowParser()
TableColumn.gdoc_parser = TableColumnParser()
Table.gdoc_parser = TableParser()
