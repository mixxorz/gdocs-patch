from typing import Any

from gdocs_patch.models.base import UNSET, Dimension
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
            columns=(
                [
                    SectionColumn.gdoc_parser.parse(column)
                    for column in data["columnProperties"]
                ]
                if "columnProperties" in data
                else UNSET
            ),
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
            margin_top=(
                Dimension.gdoc_parser.parse(data["marginTop"])
                if "marginTop" in data
                else UNSET
            ),
            margin_bottom=(
                Dimension.gdoc_parser.parse(data["marginBottom"])
                if "marginBottom" in data
                else UNSET
            ),
            margin_left=(
                Dimension.gdoc_parser.parse(data["marginLeft"])
                if "marginLeft" in data
                else UNSET
            ),
            margin_right=(
                Dimension.gdoc_parser.parse(data["marginRight"])
                if "marginRight" in data
                else UNSET
            ),
            margin_header=(
                Dimension.gdoc_parser.parse(data["marginHeader"])
                if "marginHeader" in data
                else UNSET
            ),
            margin_footer=(
                Dimension.gdoc_parser.parse(data["marginFooter"])
                if "marginFooter" in data
                else UNSET
            ),
        )


class SectionBreakParser(GDocParser[SectionBreak]):
    def parse(self, data: Any) -> SectionBreak:
        return SectionBreak(style=SectionStyle.gdoc_parser.parse(data["sectionStyle"]))


SectionColumn.gdoc_parser = SectionColumnParser()
SectionStyle.gdoc_parser = SectionStyleParser()
SectionBreak.gdoc_parser = SectionBreakParser()
