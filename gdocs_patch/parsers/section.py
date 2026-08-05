from gdocs_patch.models.base import UNSET, Dimension, UnsetType
from gdocs_patch.models.section import SectionBreak, SectionColumn, SectionStyle

from .base import (
    GDocParser,
    JsonObject,
    JsonValue,
    array_value,
    field_path,
    index_path,
    object_value,
    optional_boolean_field,
    optional_integer_field,
    optional_literal_field,
    optional_string_field,
    required_field,
)


class SectionColumnParser(GDocParser[SectionColumn]):
    def parse(self, data: JsonValue, *, path: str = "$") -> SectionColumn:
        value = object_value(data, path)
        return SectionColumn(
            width=self._required_dimension(value, "width", path),
            padding_end=self._required_dimension(value, "paddingEnd", path),
        )

    @staticmethod
    def _required_dimension(value: JsonObject, key: str, path: str) -> Dimension:
        return Dimension.gdoc_parser.parse(
            required_field(value, key, path), path=field_path(path, key)
        )


class SectionStyleParser(GDocParser[SectionStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> SectionStyle:
        value = object_value(data, path)
        return SectionStyle(
            columns=self._optional_columns(value, path),
            column_separator_style=optional_literal_field(
                value,
                "columnSeparatorStyle",
                (
                    "COLUMN_SEPARATOR_STYLE_UNSPECIFIED",
                    "NONE",
                    "BETWEEN_EACH_COLUMN",
                ),
                path,
            ),
            content_direction=optional_literal_field(
                value,
                "contentDirection",
                (
                    "CONTENT_DIRECTION_UNSPECIFIED",
                    "LEFT_TO_RIGHT",
                    "RIGHT_TO_LEFT",
                ),
                path,
            ),
            section_type=optional_literal_field(
                value,
                "sectionType",
                ("SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"),
                path,
            ),
            default_header_id=optional_string_field(value, "defaultHeaderId", path),
            default_footer_id=optional_string_field(value, "defaultFooterId", path),
            even_page_header_id=optional_string_field(value, "evenPageHeaderId", path),
            even_page_footer_id=optional_string_field(value, "evenPageFooterId", path),
            first_page_header_id=optional_string_field(
                value, "firstPageHeaderId", path
            ),
            first_page_footer_id=optional_string_field(
                value, "firstPageFooterId", path
            ),
            use_first_page_header_footer=optional_boolean_field(
                value, "useFirstPageHeaderFooter", path
            ),
            flip_page_orientation=optional_boolean_field(
                value, "flipPageOrientation", path
            ),
            page_number_start=optional_integer_field(value, "pageNumberStart", path),
            margin_top=self._optional_dimension(value, "marginTop", path),
            margin_bottom=self._optional_dimension(value, "marginBottom", path),
            margin_left=self._optional_dimension(value, "marginLeft", path),
            margin_right=self._optional_dimension(value, "marginRight", path),
            margin_header=self._optional_dimension(value, "marginHeader", path),
            margin_footer=self._optional_dimension(value, "marginFooter", path),
        )

    @staticmethod
    def _optional_columns(
        value: JsonObject, path: str
    ) -> list[SectionColumn] | UnsetType:
        if "columnProperties" not in value:
            return UNSET
        columns_path = field_path(path, "columnProperties")
        columns = array_value(value["columnProperties"], columns_path)
        return [
            SectionColumn.gdoc_parser.parse(
                column, path=index_path(columns_path, index)
            )
            for index, column in enumerate(columns)
        ]

    @staticmethod
    def _optional_dimension(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return Dimension.gdoc_parser.parse(value[key], path=field_path(path, key))


class SectionBreakParser(GDocParser[SectionBreak]):
    def parse(self, data: JsonValue, *, path: str = "$") -> SectionBreak:
        value = object_value(data, path)
        style_path = field_path(path, "sectionStyle")
        return SectionBreak(
            style=SectionStyle.gdoc_parser.parse(
                required_field(value, "sectionStyle", path), path=style_path
            )
        )


SectionColumn.gdoc_parser = SectionColumnParser()
SectionStyle.gdoc_parser = SectionStyleParser()
SectionBreak.gdoc_parser = SectionBreakParser()
