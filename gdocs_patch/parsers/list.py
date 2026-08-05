from typing import Any

from gdocs_patch.models.base import UNSET, Dimension
from gdocs_patch.models.list import ListDefinition, ListLevel
from gdocs_patch.models.paragraph import TextStyle

from .base import GDocParser


class ListLevelParser(GDocParser[ListLevel]):
    def parse(self, data: Any) -> ListLevel:
        return ListLevel(
            glyph_format=data["glyphFormat"],
            glyph_type=data.get("glyphType", UNSET),
            glyph_symbol=data.get("glyphSymbol", UNSET),
            alignment=data.get("bulletAlignment", "BULLET_ALIGNMENT_UNSPECIFIED"),
            indent_first_line=(
                Dimension.gdoc_parser.parse(data["indentFirstLine"])
                if "indentFirstLine" in data
                else UNSET
            ),
            indent_start=(
                Dimension.gdoc_parser.parse(data["indentStart"])
                if "indentStart" in data
                else UNSET
            ),
            start_number=data.get("startNumber", 0),
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class ListDefinitionParser(GDocParser[ListDefinition]):
    def parse(self, data: Any) -> ListDefinition:
        properties = data.get("listProperties", {})
        return ListDefinition(
            levels=[
                ListLevel.gdoc_parser.parse(level)
                for level in properties.get("nestingLevels", [])
            ]
        )


ListLevel.gdoc_parser = ListLevelParser()
ListDefinition.gdoc_parser = ListDefinitionParser()
