from typing import Any

from gdocs_patch.models.base import UNSET, Color, Dimension
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

from .base import GDocParser


class TableCellBorderParser(GDocParser[TableCellBorder]):
    def parse(self, data: Any) -> TableCellBorder:
        return TableCellBorder(
            color=(
                None
                if data["color"] == {}
                else Color.gdoc_parser.parse(data["color"]["color"])
            ),
            width=Dimension.gdoc_parser.parse(data["width"]),
            dash_style=data["dashStyle"],
        )


class TableCellStyleParser(GDocParser[TableCellStyle]):
    def parse(self, data: Any) -> TableCellStyle:
        return TableCellStyle(
            row_span=data.get("rowSpan", 1),
            column_span=data.get("columnSpan", 1),
            background_color=(
                None
                if data.get("backgroundColor", UNSET) == {}
                else (
                    Color.gdoc_parser.parse(data["backgroundColor"]["color"])
                    if "backgroundColor" in data
                    else UNSET
                )
            ),
            border_left=(
                TableCellBorder.gdoc_parser.parse(data["borderLeft"])
                if "borderLeft" in data
                else UNSET
            ),
            border_right=(
                TableCellBorder.gdoc_parser.parse(data["borderRight"])
                if "borderRight" in data
                else UNSET
            ),
            border_top=(
                TableCellBorder.gdoc_parser.parse(data["borderTop"])
                if "borderTop" in data
                else UNSET
            ),
            border_bottom=(
                TableCellBorder.gdoc_parser.parse(data["borderBottom"])
                if "borderBottom" in data
                else UNSET
            ),
            padding_left=(
                Dimension.gdoc_parser.parse(data["paddingLeft"])
                if "paddingLeft" in data
                else UNSET
            ),
            padding_right=(
                Dimension.gdoc_parser.parse(data["paddingRight"])
                if "paddingRight" in data
                else UNSET
            ),
            padding_top=(
                Dimension.gdoc_parser.parse(data["paddingTop"])
                if "paddingTop" in data
                else UNSET
            ),
            padding_bottom=(
                Dimension.gdoc_parser.parse(data["paddingBottom"])
                if "paddingBottom" in data
                else UNSET
            ),
            content_alignment=data.get("contentAlignment", UNSET),
        )


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
        return Table(
            rows=[TableRow.gdoc_parser.parse(row) for row in data.get("tableRows", [])],
            column_styles=(
                [
                    TableColumn.gdoc_parser.parse(column)
                    for column in data["tableStyle"].get("tableColumnProperties", [])
                ]
                if "tableStyle" in data
                else UNSET
            ),
        )


TableCellBorder.gdoc_parser = TableCellBorderParser()
TableCellStyle.gdoc_parser = TableCellStyleParser()
TableCell.gdoc_parser = TableCellParser()
TableRow.gdoc_parser = TableRowParser()
TableColumn.gdoc_parser = TableColumnParser()
Table.gdoc_parser = TableParser()
