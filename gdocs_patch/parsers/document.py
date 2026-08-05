from typing import Any

from gdocs_patch.models.base import UNSET, Dimension, UnsetType
from gdocs_patch.models.document import (
    Document,
    DocumentStyle,
    DocumentTab,
    Segment,
    StructuralElement,
    Tab,
    TableOfContents,
)
from gdocs_patch.models.list import ListDefinition
from gdocs_patch.models.paragraph import NamedStyle, Paragraph
from gdocs_patch.models.section import SectionBreak
from gdocs_patch.models.table import Table

from .base import GDocParser, parse_optional_color


class DocumentStyleParser(GDocParser[DocumentStyle]):
    def parse(self, data: Any) -> DocumentStyle:
        background = data.get("background", UNSET)
        document_format = data.get("documentFormat", UNSET)
        page_size = data.get("pageSize", UNSET)
        return DocumentStyle(
            background_color=(
                UNSET
                if isinstance(background, UnsetType) or "color" not in background
                else parse_optional_color(background["color"])
            ),
            document_mode=(
                UNSET
                if isinstance(document_format, UnsetType)
                else document_format.get("documentMode", UNSET)
            ),
            page_width=self._optional_nested_dimension(page_size, "width"),
            page_height=self._optional_nested_dimension(page_size, "height"),
            margin_top=self._optional_dimension(data, "marginTop"),
            margin_bottom=self._optional_dimension(data, "marginBottom"),
            margin_left=self._optional_dimension(data, "marginLeft"),
            margin_right=self._optional_dimension(data, "marginRight"),
            margin_header=self._optional_dimension(data, "marginHeader"),
            margin_footer=self._optional_dimension(data, "marginFooter"),
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

    @staticmethod
    def _optional_dimension(data: Any, key: str) -> Dimension | UnsetType:
        if key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])

    @staticmethod
    def _optional_nested_dimension(
        data: Any | UnsetType, key: str
    ) -> Dimension | UnsetType:
        if isinstance(data, UnsetType) or key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])


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
        return Segment(segment_id=segment_id, content=parsed_content)


class TableOfContentsParser(GDocParser[TableOfContents]):
    def parse(self, data: Any) -> TableOfContents:
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
        return TableOfContents(content=parsed_content)


class DocumentTabParser(GDocParser[DocumentTab]):
    def parse(self, data: Any) -> DocumentTab:
        body: list[StructuralElement] | UnsetType = UNSET
        if "body" in data:
            body = []
            for wrapper in data["body"].get("content", []):
                if "paragraph" in wrapper:
                    body.append(Paragraph.gdoc_parser.parse(wrapper["paragraph"]))
                elif "sectionBreak" in wrapper:
                    body.append(SectionBreak.gdoc_parser.parse(wrapper["sectionBreak"]))
                elif "table" in wrapper:
                    body.append(Table.gdoc_parser.parse(wrapper["table"]))
                else:
                    body.append(
                        TableOfContents.gdoc_parser.parse(wrapper["tableOfContents"])
                    )
        return DocumentTab(
            body=body,
            headers=self._optional_segments(data, "headers"),
            footers=self._optional_segments(data, "footers"),
            footnotes=self._optional_segments(data, "footnotes"),
            document_style=(
                DocumentStyle.gdoc_parser.parse(data["documentStyle"])
                if "documentStyle" in data
                else UNSET
            ),
            named_styles=self._optional_named_styles(data),
            lists=self._optional_lists(data),
        )

    @staticmethod
    def _optional_segments(data: Any, key: str) -> dict[str, Segment] | UnsetType:
        if key not in data:
            return UNSET
        return {
            segment_id: Segment.gdoc_parser.parse(segment)
            for segment_id, segment in data[key].items()
        }

    @staticmethod
    def _optional_named_styles(data: Any) -> list[NamedStyle] | UnsetType:
        if "namedStyles" not in data:
            return UNSET
        return [
            NamedStyle.gdoc_parser.parse(style)
            for style in data["namedStyles"].get("styles", [])
        ]

    @staticmethod
    def _optional_lists(data: Any) -> dict[str, ListDefinition] | UnsetType:
        if "lists" not in data:
            return UNSET
        return {
            list_id: ListDefinition.gdoc_parser.parse(definition)
            for list_id, definition in data["lists"].items()
        }


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
                DocumentTab.gdoc_parser.parse(data["documentTab"])
                if "documentTab" in data
                else UNSET
            ),
            children=[
                Tab.gdoc_parser.parse(child) for child in data.get("childTabs", [])
            ],
        )


class DocumentParser(GDocParser[Document]):
    def parse(self, data: Any) -> Document:
        return Document(
            document_id=data["documentId"],
            title=data["title"],
            revision_id=data.get("revisionId", UNSET),
            suggestions_view_mode=data.get("suggestionsViewMode", UNSET),
            tabs=[Tab.gdoc_parser.parse(tab) for tab in data["tabs"]],
        )


DocumentStyle.gdoc_parser = DocumentStyleParser()
Segment.gdoc_parser = SegmentParser()
TableOfContents.gdoc_parser = TableOfContentsParser()
DocumentTab.gdoc_parser = DocumentTabParser()
Tab.gdoc_parser = TabParser()
Document.gdoc_parser = DocumentParser()
