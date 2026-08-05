from typing import Any

from gdocs_patch.models.base import UNSET
from gdocs_patch.models.document import StructuralElement, TableOfContents
from gdocs_patch.models.table import (
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableRow,
)

from .base import GDocParser, color_parser, dimension_parser
from .paragraph import paragraph_parser
from .section import section_break_parser


class TableCellBorderParser(GDocParser[TableCellBorder]):
    def parse(self, data: Any) -> TableCellBorder:
        return TableCellBorder(
            color=(
                None
                if data["color"] == {}
                else color_parser.parse(data["color"]["color"])
            ),
            width=dimension_parser.parse(data["width"]),
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
                    color_parser.parse(data["backgroundColor"]["color"])
                    if "backgroundColor" in data
                    else UNSET
                )
            ),
            border_left=(
                table_cell_border_parser.parse(data["borderLeft"])
                if "borderLeft" in data
                else UNSET
            ),
            border_right=(
                table_cell_border_parser.parse(data["borderRight"])
                if "borderRight" in data
                else UNSET
            ),
            border_top=(
                table_cell_border_parser.parse(data["borderTop"])
                if "borderTop" in data
                else UNSET
            ),
            border_bottom=(
                table_cell_border_parser.parse(data["borderBottom"])
                if "borderBottom" in data
                else UNSET
            ),
            padding_left=(
                dimension_parser.parse(data["paddingLeft"])
                if "paddingLeft" in data
                else UNSET
            ),
            padding_right=(
                dimension_parser.parse(data["paddingRight"])
                if "paddingRight" in data
                else UNSET
            ),
            padding_top=(
                dimension_parser.parse(data["paddingTop"])
                if "paddingTop" in data
                else UNSET
            ),
            padding_bottom=(
                dimension_parser.parse(data["paddingBottom"])
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
                parsed_content.append(paragraph_parser.parse(wrapper["paragraph"]))
            elif "sectionBreak" in wrapper:
                parsed_content.append(
                    section_break_parser.parse(wrapper["sectionBreak"])
                )
            elif "table" in wrapper:
                parsed_content.append(table_parser.parse(wrapper["table"]))
            else:
                parsed_content.append(
                    table_of_contents_parser.parse(wrapper["tableOfContents"])
                )
        return TableCell(
            content=parsed_content,
            style=(
                table_cell_style_parser.parse(data["tableCellStyle"])
                if "tableCellStyle" in data
                else UNSET
            ),
        )


class TableRowParser(GDocParser[TableRow]):
    def parse(self, data: Any) -> TableRow:
        style = data.get("tableRowStyle", {})
        return TableRow(
            cells=[
                table_cell_parser.parse(cell) for cell in data.get("tableCells", [])
            ],
            min_height=(
                dimension_parser.parse(style["minRowHeight"])
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
            width=(dimension_parser.parse(data["width"]) if "width" in data else UNSET),
        )


class TableParser(GDocParser[Table]):
    def parse(self, data: Any) -> Table:
        return Table(
            rows=[table_row_parser.parse(row) for row in data.get("tableRows", [])],
            column_styles=(
                [
                    table_column_parser.parse(column)
                    for column in data["tableStyle"].get("tableColumnProperties", [])
                ]
                if "tableStyle" in data
                else UNSET
            ),
        )


class TableOfContentsParser(GDocParser[TableOfContents]):
    def parse(self, data: Any) -> TableOfContents:
        parsed_content: list[StructuralElement] = []
        for wrapper in data.get("content", []):
            if "paragraph" in wrapper:
                parsed_content.append(paragraph_parser.parse(wrapper["paragraph"]))
            elif "sectionBreak" in wrapper:
                parsed_content.append(
                    section_break_parser.parse(wrapper["sectionBreak"])
                )
            elif "table" in wrapper:
                parsed_content.append(table_parser.parse(wrapper["table"]))
            else:
                parsed_content.append(
                    table_of_contents_parser.parse(wrapper["tableOfContents"])
                )
        return TableOfContents(content=parsed_content)


table_cell_border_parser = TableCellBorderParser()
table_cell_style_parser = TableCellStyleParser()
table_cell_parser = TableCellParser()
table_row_parser = TableRowParser()
table_column_parser = TableColumnParser()
table_parser = TableParser()
table_of_contents_parser = TableOfContentsParser()
