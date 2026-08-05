from typing import Any

from gdocs_patch.models.base import UNSET, UnsetType
from gdocs_patch.models.document import (
    Document,
    DocumentStyle,
    DocumentTab,
    Segment,
    StructuralElement,
    Tab,
)

from .base import GDocParser, color_parser, dimension_parser
from .list import list_definition_parser
from .paragraph import named_style_parser, paragraph_parser
from .section import section_break_parser
from .table import table_of_contents_parser, table_parser


class DocumentStyleParser(GDocParser[DocumentStyle]):
    def parse(self, data: Any) -> DocumentStyle:
        background = data.get("background", {})
        document_format = data.get("documentFormat", {})
        page_size = data.get("pageSize", {})
        return DocumentStyle(
            background_color=(
                None
                if background.get("color", UNSET) == {}
                else (
                    color_parser.parse(background["color"]["color"])
                    if "color" in background
                    else UNSET
                )
            ),
            document_mode=document_format.get("documentMode", UNSET),
            page_width=(
                dimension_parser.parse(page_size["width"])
                if "width" in page_size
                else UNSET
            ),
            page_height=(
                dimension_parser.parse(page_size["height"])
                if "height" in page_size
                else UNSET
            ),
            margin_top=(
                dimension_parser.parse(data["marginTop"])
                if "marginTop" in data
                else UNSET
            ),
            margin_bottom=(
                dimension_parser.parse(data["marginBottom"])
                if "marginBottom" in data
                else UNSET
            ),
            margin_left=(
                dimension_parser.parse(data["marginLeft"])
                if "marginLeft" in data
                else UNSET
            ),
            margin_right=(
                dimension_parser.parse(data["marginRight"])
                if "marginRight" in data
                else UNSET
            ),
            margin_header=(
                dimension_parser.parse(data["marginHeader"])
                if "marginHeader" in data
                else UNSET
            ),
            margin_footer=(
                dimension_parser.parse(data["marginFooter"])
                if "marginFooter" in data
                else UNSET
            ),
            default_header_id=data.get("defaultHeaderId", UNSET),
            default_footer_id=data.get("defaultFooterId", UNSET),
            even_page_header_id=data.get("evenPageHeaderId", UNSET),
            even_page_footer_id=data.get("evenPageFooterId", UNSET),
            first_page_header_id=data.get("firstPageHeaderId", UNSET),
            first_page_footer_id=data.get("firstPageFooterId", UNSET),
            use_even_page_header_footer=data.get("useEvenPageHeaderFooter", UNSET),
            use_first_page_header_footer=data.get("useFirstPageHeaderFooter", UNSET),
            use_custom_header_footer_margins=data.get(
                "useCustomHeaderFooterMargins", UNSET
            ),
            flip_page_orientation=data.get("flipPageOrientation", UNSET),
            page_number_start=data.get("pageNumberStart", UNSET),
        )


class SegmentParser(GDocParser[Segment]):
    def parse(self, data: Any) -> Segment:
        if "headerId" in data:
            segment_id = data["headerId"]
        elif "footerId" in data:
            segment_id = data["footerId"]
        else:
            segment_id = data["footnoteId"]
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
        return Segment(segment_id=segment_id, content=parsed_content)


class DocumentTabParser(GDocParser[DocumentTab]):
    def parse(self, data: Any) -> DocumentTab:
        body: list[StructuralElement] | UnsetType = UNSET
        if "body" in data:
            body = []
            for wrapper in data["body"].get("content", []):
                if "paragraph" in wrapper:
                    body.append(paragraph_parser.parse(wrapper["paragraph"]))
                elif "sectionBreak" in wrapper:
                    body.append(section_break_parser.parse(wrapper["sectionBreak"]))
                elif "table" in wrapper:
                    body.append(table_parser.parse(wrapper["table"]))
                else:
                    body.append(
                        table_of_contents_parser.parse(wrapper["tableOfContents"])
                    )
        return DocumentTab(
            body=body,
            headers=(
                {
                    segment_id: segment_parser.parse(segment)
                    for segment_id, segment in data["headers"].items()
                }
                if "headers" in data
                else UNSET
            ),
            footers=(
                {
                    segment_id: segment_parser.parse(segment)
                    for segment_id, segment in data["footers"].items()
                }
                if "footers" in data
                else UNSET
            ),
            footnotes=(
                {
                    segment_id: segment_parser.parse(segment)
                    for segment_id, segment in data["footnotes"].items()
                }
                if "footnotes" in data
                else UNSET
            ),
            document_style=(
                document_style_parser.parse(data["documentStyle"])
                if "documentStyle" in data
                else UNSET
            ),
            named_styles=(
                [
                    named_style_parser.parse(style)
                    for style in data["namedStyles"].get("styles", [])
                ]
                if "namedStyles" in data
                else UNSET
            ),
            lists=(
                {
                    list_id: list_definition_parser.parse(definition)
                    for list_id, definition in data["lists"].items()
                }
                if "lists" in data
                else UNSET
            ),
        )


class TabParser(GDocParser[Tab]):
    def parse(self, data: Any) -> Tab:
        properties = data["tabProperties"]
        return Tab(
            tab_id=properties["tabId"],
            title=properties["title"],
            index=properties["index"],
            nesting_level=properties.get("nestingLevel", 0),
            parent_tab_id=properties.get("parentTabId", UNSET),
            icon_emoji=properties.get("iconEmoji", UNSET),
            content=(
                document_tab_parser.parse(data["documentTab"])
                if "documentTab" in data
                else UNSET
            ),
            children=[tab_parser.parse(child) for child in data.get("childTabs", [])],
        )


class DocumentParser(GDocParser[Document]):
    def parse(self, data: Any) -> Document:
        return Document(
            document_id=data["documentId"],
            title=data["title"],
            revision_id=data.get("revisionId", UNSET),
            suggestions_view_mode=data.get("suggestionsViewMode", UNSET),
            tabs=[tab_parser.parse(tab) for tab in data["tabs"]],
        )


document_style_parser = DocumentStyleParser()
segment_parser = SegmentParser()
document_tab_parser = DocumentTabParser()
tab_parser = TabParser()
document_parser = DocumentParser()
