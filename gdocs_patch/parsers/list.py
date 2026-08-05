from gdocs_patch.models.base import UNSET, Dimension, UnsetType
from gdocs_patch.models.list import ListDefinition, ListLevel
from gdocs_patch.models.paragraph import TextStyle

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
    optional_literal_field,
    optional_string_field,
    required_field,
    string_value,
)


class ListLevelParser(GDocParser[ListLevel]):
    def parse(self, data: JsonValue, *, path: str = "$") -> ListLevel:
        value = object_value(data, path)
        try:
            return ListLevel(
                glyph_format=string_value(
                    required_field(value, "glyphFormat", path),
                    field_path(path, "glyphFormat"),
                ),
                glyph_type=optional_literal_field(
                    value,
                    "glyphType",
                    (
                        "GLYPH_TYPE_UNSPECIFIED",
                        "NONE",
                        "DECIMAL",
                        "ZERO_DECIMAL",
                        "UPPER_ALPHA",
                        "ALPHA",
                        "UPPER_ROMAN",
                        "ROMAN",
                    ),
                    path,
                ),
                glyph_symbol=optional_string_field(value, "glyphSymbol", path),
                alignment=(
                    literal_value(
                        value["bulletAlignment"],
                        ("BULLET_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"),
                        field_path(path, "bulletAlignment"),
                    )
                    if "bulletAlignment" in value
                    else "BULLET_ALIGNMENT_UNSPECIFIED"
                ),
                indent_first_line=self._optional_dimension(
                    value, "indentFirstLine", path
                ),
                indent_start=self._optional_dimension(value, "indentStart", path),
                start_number=(
                    integer_value(value["startNumber"], field_path(path, "startNumber"))
                    if "startNumber" in value
                    else 0
                ),
                text_style=(
                    TextStyle.gdoc_parser.parse(
                        value["textStyle"], path=field_path(path, "textStyle")
                    )
                    if "textStyle" in value
                    else UNSET
                ),
            )
        except ValueError as error:
            if isinstance(error, GDocParseError):
                raise
            raise GDocParseError(path, str(error)) from error

    @staticmethod
    def _optional_dimension(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return Dimension.gdoc_parser.parse(value[key], path=field_path(path, key))


class ListDefinitionParser(GDocParser[ListDefinition]):
    def parse(self, data: JsonValue, *, path: str = "$") -> ListDefinition:
        value = object_value(data, path)
        if "listProperties" not in value:
            return ListDefinition(levels=[])
        properties_path = field_path(path, "listProperties")
        properties = object_value(value["listProperties"], properties_path)
        levels_path = field_path(properties_path, "nestingLevels")
        levels = (
            array_value(properties["nestingLevels"], levels_path)
            if "nestingLevels" in properties
            else []
        )
        return ListDefinition(
            levels=[
                ListLevel.gdoc_parser.parse(level, path=index_path(levels_path, index))
                for index, level in enumerate(levels)
            ]
        )


ListLevel.gdoc_parser = ListLevelParser()
ListDefinition.gdoc_parser = ListDefinitionParser()
