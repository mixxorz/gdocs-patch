from typing import Literal, cast

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
    map_key_path,
    object_value,
    optional_boolean_field,
    optional_integer_field,
    optional_string_field,
    parse_optional_color,
    required_field,
    string_value,
)


class DocumentStyleParser(GDocParser[DocumentStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> DocumentStyle:
        value = object_value(data, path)
        background = self._optional_object(value, "background", path)
        background_path = field_path(path, "background")
        document_format = self._optional_object(value, "documentFormat", path)
        format_path = field_path(path, "documentFormat")
        page_size = self._optional_object(value, "pageSize", path)
        page_size_path = field_path(path, "pageSize")
        document_mode: (
            Literal["DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"] | UnsetType
        ) = (
            UNSET
            if isinstance(document_format, UnsetType)
            or "documentMode" not in document_format
            else cast(
                Literal["DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"],
                literal_value(
                    document_format["documentMode"],
                    ("DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"),
                    field_path(format_path, "documentMode"),
                ),
            )
        )
        return DocumentStyle(
            background_color=(
                UNSET
                if isinstance(background, UnsetType) or "color" not in background
                else parse_optional_color(
                    background["color"], field_path(background_path, "color")
                )
            ),
            document_mode=document_mode,
            page_width=self._optional_nested_dimension(
                page_size, "width", page_size_path
            ),
            page_height=self._optional_nested_dimension(
                page_size, "height", page_size_path
            ),
            margin_top=self._optional_dimension(value, "marginTop", path),
            margin_bottom=self._optional_dimension(value, "marginBottom", path),
            margin_left=self._optional_dimension(value, "marginLeft", path),
            margin_right=self._optional_dimension(value, "marginRight", path),
            margin_header=self._optional_dimension(value, "marginHeader", path),
            margin_footer=self._optional_dimension(value, "marginFooter", path),
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
            use_even_page_header_footer=optional_boolean_field(
                value, "useEvenPageHeaderFooter", path
            ),
            use_first_page_header_footer=optional_boolean_field(
                value, "useFirstPageHeaderFooter", path
            ),
            use_custom_header_footer_margins=optional_boolean_field(
                value, "useCustomHeaderFooterMargins", path
            ),
            flip_page_orientation=optional_boolean_field(
                value, "flipPageOrientation", path
            ),
            page_number_start=optional_integer_field(value, "pageNumberStart", path),
        )

    @staticmethod
    def _optional_object(
        value: JsonObject, key: str, path: str
    ) -> JsonObject | UnsetType:
        if key not in value:
            return UNSET
        return object_value(value[key], field_path(path, key))

    @staticmethod
    def _optional_dimension(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return Dimension.gdoc_parser.parse(value[key], path=field_path(path, key))

    @staticmethod
    def _optional_nested_dimension(
        value: JsonObject | UnsetType, key: str, path: str
    ) -> Dimension | UnsetType:
        if isinstance(value, UnsetType) or key not in value:
            return UNSET
        return Dimension.gdoc_parser.parse(value[key], path=field_path(path, key))


class SegmentParser(GDocParser[Segment]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Segment:
        value = object_value(data, path)
        id_keys = ("headerId", "footerId", "footnoteId")
        present_ids = [key for key in id_keys if key in value]
        if len(present_ids) != 1:
            raise GDocParseError(path, "expected exactly one supported segment ID")
        id_key = present_ids[0]
        content_path = field_path(path, "content")
        content = (
            array_value(value["content"], content_path) if "content" in value else []
        )
        parsed_content: list[StructuralElement] = []
        for index, item in enumerate(content):
            item_path = index_path(content_path, index)
            wrapper = object_value(item, item_path)
            keys = ("paragraph", "sectionBreak", "table", "tableOfContents")
            present = [key for key in keys if key in wrapper]
            if len(present) != 1:
                raise GDocParseError(
                    item_path, "expected exactly one supported structural element"
                )
            key = present[0]
            inner = wrapper[key]
            inner_path = field_path(item_path, key)
            if key == "paragraph":
                parsed_content.append(
                    Paragraph.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "sectionBreak":
                parsed_content.append(
                    SectionBreak.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "table":
                parsed_content.append(Table.gdoc_parser.parse(inner, path=inner_path))
            else:
                parsed_content.append(
                    TableOfContents.gdoc_parser.parse(inner, path=inner_path)
                )
        return Segment(
            segment_id=string_value(value[id_key], field_path(path, id_key)),
            content=parsed_content,
        )


class TableOfContentsParser(GDocParser[TableOfContents]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TableOfContents:
        value = object_value(data, path)
        content_path = field_path(path, "content")
        content = (
            array_value(value["content"], content_path) if "content" in value else []
        )
        parsed_content: list[StructuralElement] = []
        for index, item in enumerate(content):
            item_path = index_path(content_path, index)
            wrapper = object_value(item, item_path)
            keys = ("paragraph", "sectionBreak", "table", "tableOfContents")
            present = [key for key in keys if key in wrapper]
            if len(present) != 1:
                raise GDocParseError(
                    item_path, "expected exactly one supported structural element"
                )
            key = present[0]
            inner = wrapper[key]
            inner_path = field_path(item_path, key)
            if key == "paragraph":
                parsed_content.append(
                    Paragraph.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "sectionBreak":
                parsed_content.append(
                    SectionBreak.gdoc_parser.parse(inner, path=inner_path)
                )
            elif key == "table":
                parsed_content.append(Table.gdoc_parser.parse(inner, path=inner_path))
            else:
                parsed_content.append(
                    TableOfContents.gdoc_parser.parse(inner, path=inner_path)
                )
        return TableOfContents(content=parsed_content)


class DocumentTabParser(GDocParser[DocumentTab]):
    def parse(self, data: JsonValue, *, path: str = "$") -> DocumentTab:
        value = object_value(data, path)
        body: list[StructuralElement] | UnsetType = UNSET
        if "body" in value:
            body_path = field_path(path, "body")
            body_value = object_value(value["body"], body_path)
            content_path = field_path(body_path, "content")
            content = (
                array_value(body_value["content"], content_path)
                if "content" in body_value
                else []
            )
            body = []
            for index, item in enumerate(content):
                item_path = index_path(content_path, index)
                wrapper = object_value(item, item_path)
                keys = ("paragraph", "sectionBreak", "table", "tableOfContents")
                present = [key for key in keys if key in wrapper]
                if len(present) != 1:
                    raise GDocParseError(
                        item_path, "expected exactly one supported structural element"
                    )
                key = present[0]
                inner = wrapper[key]
                inner_path = field_path(item_path, key)
                if key == "paragraph":
                    body.append(Paragraph.gdoc_parser.parse(inner, path=inner_path))
                elif key == "sectionBreak":
                    body.append(SectionBreak.gdoc_parser.parse(inner, path=inner_path))
                elif key == "table":
                    body.append(Table.gdoc_parser.parse(inner, path=inner_path))
                else:
                    body.append(
                        TableOfContents.gdoc_parser.parse(inner, path=inner_path)
                    )
        return DocumentTab(
            body=body,
            headers=self._optional_segments(value, "headers", path),
            footers=self._optional_segments(value, "footers", path),
            footnotes=self._optional_segments(value, "footnotes", path),
            document_style=(
                DocumentStyle.gdoc_parser.parse(
                    value["documentStyle"], path=field_path(path, "documentStyle")
                )
                if "documentStyle" in value
                else UNSET
            ),
            named_styles=self._optional_named_styles(value, path),
            lists=self._optional_lists(value, path),
        )

    @staticmethod
    def _optional_segments(
        value: JsonObject, key: str, path: str
    ) -> dict[str, Segment] | UnsetType:
        if key not in value:
            return UNSET
        map_path = field_path(path, key)
        segments = object_value(value[key], map_path)
        return {
            segment_id: Segment.gdoc_parser.parse(
                segment, path=map_key_path(map_path, segment_id)
            )
            for segment_id, segment in segments.items()
        }

    @staticmethod
    def _optional_named_styles(
        value: JsonObject, path: str
    ) -> list[NamedStyle] | UnsetType:
        if "namedStyles" not in value:
            return UNSET
        named_path = field_path(path, "namedStyles")
        named = object_value(value["namedStyles"], named_path)
        styles_path = field_path(named_path, "styles")
        styles = array_value(named["styles"], styles_path) if "styles" in named else []
        return [
            NamedStyle.gdoc_parser.parse(style, path=index_path(styles_path, index))
            for index, style in enumerate(styles)
        ]

    @staticmethod
    def _optional_lists(
        value: JsonObject, path: str
    ) -> dict[str, ListDefinition] | UnsetType:
        if "lists" not in value:
            return UNSET
        lists_path = field_path(path, "lists")
        lists = object_value(value["lists"], lists_path)
        return {
            list_id: ListDefinition.gdoc_parser.parse(
                definition, path=map_key_path(lists_path, list_id)
            )
            for list_id, definition in lists.items()
        }


class TabParser(GDocParser[Tab]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Tab:
        value = object_value(data, path)
        properties_path = field_path(path, "tabProperties")
        properties = object_value(
            required_field(value, "tabProperties", path), properties_path
        )
        parsed_index = integer_value(
            required_field(properties, "index", properties_path),
            field_path(properties_path, "index"),
        )
        children_path = field_path(path, "childTabs")
        children = (
            array_value(value["childTabs"], children_path)
            if "childTabs" in value
            else []
        )
        return Tab(
            tab_id=string_value(
                required_field(properties, "tabId", properties_path),
                field_path(properties_path, "tabId"),
            ),
            title=string_value(
                required_field(properties, "title", properties_path),
                field_path(properties_path, "title"),
            ),
            index=parsed_index,
            nesting_level=(
                integer_value(
                    properties["nestingLevel"],
                    field_path(properties_path, "nestingLevel"),
                )
                if "nestingLevel" in properties
                else 0
            ),
            parent_tab_id=optional_string_field(
                properties, "parentTabId", properties_path
            ),
            icon_emoji=optional_string_field(properties, "iconEmoji", properties_path),
            content=(
                DocumentTab.gdoc_parser.parse(
                    value["documentTab"], path=field_path(path, "documentTab")
                )
                if "documentTab" in value
                else UNSET
            ),
            children=[
                Tab.gdoc_parser.parse(child, path=index_path(children_path, index))
                for index, child in enumerate(children)
            ],
        )


class DocumentParser(GDocParser[Document]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Document:
        value = object_value(data, path)
        tabs_path = field_path(path, "tabs")
        tabs = array_value(required_field(value, "tabs", path), tabs_path)
        suggestions_view_mode: (
            Literal[
                "DEFAULT_FOR_CURRENT_ACCESS",
                "SUGGESTIONS_INLINE",
                "PREVIEW_SUGGESTIONS_ACCEPTED",
                "PREVIEW_WITHOUT_SUGGESTIONS",
            ]
            | UnsetType
        ) = (
            cast(
                Literal[
                    "DEFAULT_FOR_CURRENT_ACCESS",
                    "SUGGESTIONS_INLINE",
                    "PREVIEW_SUGGESTIONS_ACCEPTED",
                    "PREVIEW_WITHOUT_SUGGESTIONS",
                ],
                literal_value(
                    value["suggestionsViewMode"],
                    (
                        "DEFAULT_FOR_CURRENT_ACCESS",
                        "SUGGESTIONS_INLINE",
                        "PREVIEW_SUGGESTIONS_ACCEPTED",
                        "PREVIEW_WITHOUT_SUGGESTIONS",
                    ),
                    field_path(path, "suggestionsViewMode"),
                ),
            )
            if "suggestionsViewMode" in value
            else UNSET
        )
        return Document(
            document_id=string_value(
                required_field(value, "documentId", path),
                field_path(path, "documentId"),
            ),
            title=string_value(
                required_field(value, "title", path), field_path(path, "title")
            ),
            revision_id=optional_string_field(value, "revisionId", path),
            suggestions_view_mode=suggestions_view_mode,
            tabs=[
                Tab.gdoc_parser.parse(tab, path=index_path(tabs_path, index))
                for index, tab in enumerate(tabs)
            ],
        )


DocumentStyle.gdoc_parser = DocumentStyleParser()
Segment.gdoc_parser = SegmentParser()
TableOfContents.gdoc_parser = TableOfContentsParser()
DocumentTab.gdoc_parser = DocumentTabParser()
Tab.gdoc_parser = TabParser()
Document.gdoc_parser = DocumentParser()
