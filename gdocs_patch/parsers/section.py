from typing import Any

from gdocs_patch.models.base import UNSET, Dimension, UnsetType
from gdocs_patch.models.section import SectionBreak, SectionColumn, SectionStyle

from .base import GDocParser


class SectionColumnParser(GDocParser[SectionColumn]):
    def parse(self, data: Any) -> SectionColumn:
        return SectionColumn(
            width=Dimension.gdoc_parser.parse(data["width"]),
            padding_end=Dimension.gdoc_parser.parse(data["paddingEnd"]),
        )


class SectionStyleParser(GDocParser[SectionStyle]):
    def parse(self, data: Any) -> SectionStyle:
        return SectionStyle(
            columns=self._optional_columns(data),
            column_separator_style=data.get("columnSeparatorStyle", UNSET),
            content_direction=data.get("contentDirection", UNSET),
            section_type=data.get("sectionType", UNSET),
            default_header_id=data.get("defaultHeaderId", UNSET),
            default_footer_id=data.get("defaultFooterId", UNSET),
            even_page_header_id=data.get("evenPageHeaderId", UNSET),
            even_page_footer_id=data.get("evenPageFooterId", UNSET),
            first_page_header_id=data.get("firstPageHeaderId", UNSET),
            first_page_footer_id=data.get("firstPageFooterId", UNSET),
            use_first_page_header_footer=data.get("useFirstPageHeaderFooter", UNSET),
            flip_page_orientation=data.get("flipPageOrientation", UNSET),
            page_number_start=data.get("pageNumberStart", UNSET),
            margin_top=self._optional_dimension(data, "marginTop"),
            margin_bottom=self._optional_dimension(data, "marginBottom"),
            margin_left=self._optional_dimension(data, "marginLeft"),
            margin_right=self._optional_dimension(data, "marginRight"),
            margin_header=self._optional_dimension(data, "marginHeader"),
            margin_footer=self._optional_dimension(data, "marginFooter"),
        )

    @staticmethod
    def _optional_columns(data: Any) -> list[SectionColumn] | UnsetType:
        if "columnProperties" not in data:
            return UNSET
        return [
            SectionColumn.gdoc_parser.parse(column)
            for column in data["columnProperties"]
        ]

    @staticmethod
    def _optional_dimension(data: Any, key: str) -> Dimension | UnsetType:
        if key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])


class SectionBreakParser(GDocParser[SectionBreak]):
    def parse(self, data: Any) -> SectionBreak:
        return SectionBreak(style=SectionStyle.gdoc_parser.parse(data["sectionStyle"]))


SectionColumn.gdoc_parser = SectionColumnParser()
SectionStyle.gdoc_parser = SectionStyleParser()
SectionBreak.gdoc_parser = SectionBreakParser()
