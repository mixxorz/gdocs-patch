from gdocs_patch.models.base import UNSET, Color, Dimension, UnsetType
from gdocs_patch.models.paragraph import (
    AutoText,
    BookmarkLink,
    Bullet,
    ColumnBreak,
    DateElement,
    Equation,
    FootnoteReference,
    HeadingLink,
    HorizontalRule,
    InlineObjectReference,
    Link,
    NamedStyle,
    PageBreak,
    Paragraph,
    ParagraphBorder,
    ParagraphElement,
    ParagraphStyle,
    PersonReference,
    RichLink,
    TabLink,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
)

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
    number_value,
    object_value,
    optional_boolean_field,
    optional_integer_field,
    optional_literal_field,
    optional_object_field,
    optional_string_field,
    parse_optional_color,
    required_field,
    string_value,
)


class UrlLinkParser(GDocParser[UrlLink]):
    def parse(self, data: JsonValue, *, path: str = "$") -> UrlLink:
        return UrlLink(url=string_value(data, path))


class TabLinkParser(GDocParser[TabLink]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TabLink:
        return TabLink(tab_id=string_value(data, path))


class BookmarkLinkParser(GDocParser[BookmarkLink]):
    def parse(self, data: JsonValue, *, path: str = "$") -> BookmarkLink:
        value = object_value(data, path)
        return BookmarkLink(
            bookmark_id=string_value(
                required_field(value, "id", path), field_path(path, "id")
            ),
            tab_id=optional_string_field(value, "tabId", path),
        )


class HeadingLinkParser(GDocParser[HeadingLink]):
    def parse(self, data: JsonValue, *, path: str = "$") -> HeadingLink:
        value = object_value(data, path)
        return HeadingLink(
            heading_id=string_value(
                required_field(value, "id", path), field_path(path, "id")
            ),
            tab_id=optional_string_field(value, "tabId", path),
        )


class TextStyleParser(GDocParser[TextStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TextStyle:
        value = object_value(data, path)
        weighted_font_family = optional_object_field(value, "weightedFontFamily", path)
        return TextStyle(
            bold=optional_boolean_field(value, "bold", path),
            italic=optional_boolean_field(value, "italic", path),
            underline=optional_boolean_field(value, "underline", path),
            strikethrough=optional_boolean_field(value, "strikethrough", path),
            small_caps=optional_boolean_field(value, "smallCaps", path),
            baseline_offset=optional_literal_field(
                value,
                "baselineOffset",
                (
                    "BASELINE_OFFSET_UNSPECIFIED",
                    "NONE",
                    "SUPERSCRIPT",
                    "SUBSCRIPT",
                ),
                path,
            ),
            font_size=self._optional_dimension_field(value, "fontSize", path),
            font_family=(
                UNSET
                if isinstance(weighted_font_family, UnsetType)
                else optional_string_field(
                    weighted_font_family,
                    "fontFamily",
                    field_path(path, "weightedFontFamily"),
                )
            ),
            font_weight=(
                UNSET
                if isinstance(weighted_font_family, UnsetType)
                else optional_integer_field(
                    weighted_font_family,
                    "weight",
                    field_path(path, "weightedFontFamily"),
                )
            ),
            foreground_color=self._optional_color_field(value, "foregroundColor", path),
            background_color=self._optional_color_field(value, "backgroundColor", path),
            link=self._optional_link(value, path),
        )

    @staticmethod
    def _optional_dimension_field(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return _parse_dimension(value[key], field_path(path, key))

    @staticmethod
    def _optional_color_field(
        value: JsonObject, key: str, path: str
    ) -> Color | None | UnsetType:
        if key not in value:
            return UNSET
        return parse_optional_color(value[key], field_path(path, key))

    @staticmethod
    def _optional_link(value: JsonObject, path: str) -> Link | UnsetType:
        if "link" not in value:
            return UNSET
        link_path = field_path(path, "link")
        wrapper = object_value(value["link"], link_path)
        targets = (
            "url",
            "tabId",
            "bookmark",
            "heading",
            "bookmarkId",
            "headingId",
        )
        present = [target for target in targets if target in wrapper]
        if len(present) != 1:
            raise GDocParseError(
                link_path, "expected exactly one supported link target"
            )
        target = present[0]
        target_path = field_path(link_path, target)
        target_value = wrapper[target]
        if target == "url":
            return UrlLink.gdoc_parser.parse(target_value, path=target_path)
        if target == "tabId":
            return TabLink.gdoc_parser.parse(target_value, path=target_path)
        if target == "bookmark":
            return BookmarkLink.gdoc_parser.parse(target_value, path=target_path)
        if target == "heading":
            return HeadingLink.gdoc_parser.parse(target_value, path=target_path)
        if target == "bookmarkId":
            return BookmarkLink(bookmark_id=string_value(target_value, target_path))
        return HeadingLink(heading_id=string_value(target_value, target_path))


class BulletParser(GDocParser[Bullet]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Bullet:
        value = object_value(data, path)
        text_style = (
            TextStyle.gdoc_parser.parse(
                value["textStyle"], path=field_path(path, "textStyle")
            )
            if "textStyle" in value
            else UNSET
        )
        return Bullet(
            list_id=string_value(
                required_field(value, "listId", path), field_path(path, "listId")
            ),
            nesting_level=(
                integer_value(value["nestingLevel"], field_path(path, "nestingLevel"))
                if "nestingLevel" in value
                else 0
            ),
            text_style=text_style,
        )


class ParagraphBorderParser(GDocParser[ParagraphBorder]):
    def parse(self, data: JsonValue, *, path: str = "$") -> ParagraphBorder:
        value = object_value(data, path)
        return ParagraphBorder(
            color=parse_optional_color(
                required_field(value, "color", path), field_path(path, "color")
            ),
            width=_parse_dimension(
                required_field(value, "width", path), field_path(path, "width")
            ),
            padding=_parse_dimension(
                required_field(value, "padding", path), field_path(path, "padding")
            ),
            dash_style=literal_value(
                required_field(value, "dashStyle", path),
                ("DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"),
                field_path(path, "dashStyle"),
            ),
        )


class TabStopParser(GDocParser[TabStop]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TabStop:
        value = object_value(data, path)
        return TabStop(
            offset=_parse_dimension(
                required_field(value, "offset", path), field_path(path, "offset")
            ),
            alignment=literal_value(
                required_field(value, "alignment", path),
                ("TAB_STOP_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"),
                field_path(path, "alignment"),
            ),
        )


class ParagraphStyleParser(GDocParser[ParagraphStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> ParagraphStyle:
        value = object_value(data, path)
        return ParagraphStyle(
            named_style_type=optional_literal_field(
                value,
                "namedStyleType",
                (
                    "NAMED_STYLE_TYPE_UNSPECIFIED",
                    "NORMAL_TEXT",
                    "TITLE",
                    "SUBTITLE",
                    "HEADING_1",
                    "HEADING_2",
                    "HEADING_3",
                    "HEADING_4",
                    "HEADING_5",
                    "HEADING_6",
                ),
                path,
            ),
            alignment=optional_literal_field(
                value,
                "alignment",
                ("ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END", "JUSTIFIED"),
                path,
            ),
            direction=optional_literal_field(
                value,
                "direction",
                (
                    "CONTENT_DIRECTION_UNSPECIFIED",
                    "LEFT_TO_RIGHT",
                    "RIGHT_TO_LEFT",
                ),
                path,
            ),
            line_spacing=self._optional_number(value, "lineSpacing", path),
            spacing_mode=optional_literal_field(
                value,
                "spacingMode",
                ("SPACING_MODE_UNSPECIFIED", "NEVER_COLLAPSE", "COLLAPSE_LISTS"),
                path,
            ),
            space_above=self._optional_dimension(value, "spaceAbove", path),
            space_below=self._optional_dimension(value, "spaceBelow", path),
            indent_first_line=self._optional_dimension(value, "indentFirstLine", path),
            indent_start=self._optional_dimension(value, "indentStart", path),
            indent_end=self._optional_dimension(value, "indentEnd", path),
            keep_lines_together=optional_boolean_field(
                value, "keepLinesTogether", path
            ),
            keep_with_next=optional_boolean_field(value, "keepWithNext", path),
            avoid_widow_and_orphan=optional_boolean_field(
                value, "avoidWidowAndOrphan", path
            ),
            page_break_before=optional_boolean_field(value, "pageBreakBefore", path),
            heading_id=optional_string_field(value, "headingId", path),
            border_between=self._optional_border(value, "borderBetween", path),
            border_top=self._optional_border(value, "borderTop", path),
            border_bottom=self._optional_border(value, "borderBottom", path),
            border_left=self._optional_border(value, "borderLeft", path),
            border_right=self._optional_border(value, "borderRight", path),
            shading_color=self._optional_shading(value, path),
            tab_stops=self._optional_tab_stops(value, path),
        )

    @staticmethod
    def _optional_number(value: JsonObject, key: str, path: str) -> float | UnsetType:
        if key not in value:
            return UNSET
        return number_value(value[key], field_path(path, key))

    @staticmethod
    def _optional_dimension(
        value: JsonObject, key: str, path: str
    ) -> Dimension | UnsetType:
        if key not in value:
            return UNSET
        return _parse_dimension(value[key], field_path(path, key))

    @staticmethod
    def _optional_border(
        value: JsonObject, key: str, path: str
    ) -> ParagraphBorder | UnsetType:
        if key not in value:
            return UNSET
        return ParagraphBorder.gdoc_parser.parse(value[key], path=field_path(path, key))

    @staticmethod
    def _optional_shading(value: JsonObject, path: str) -> Color | None | UnsetType:
        if "shading" not in value:
            return UNSET
        shading_path = field_path(path, "shading")
        shading = object_value(value["shading"], shading_path)
        return parse_optional_color(
            required_field(shading, "backgroundColor", shading_path),
            field_path(shading_path, "backgroundColor"),
        )

    @staticmethod
    def _optional_tab_stops(value: JsonObject, path: str) -> list[TabStop] | UnsetType:
        if "tabStops" not in value:
            return UNSET
        tab_stops_path = field_path(path, "tabStops")
        tab_stops = required_field(value, "tabStops", path)
        if not isinstance(tab_stops, list):
            raise GDocParseError(tab_stops_path, "expected array")
        return [
            TabStop.gdoc_parser.parse(item, path=index_path(tab_stops_path, index))
            for index, item in enumerate(tab_stops)
        ]


class TextRunParser(GDocParser[TextRun]):
    def parse(self, data: JsonValue, *, path: str = "$") -> TextRun:
        value = object_value(data, path)
        return TextRun(
            content=string_value(
                required_field(value, "content", path), field_path(path, "content")
            ),
            text_style=_optional_text_style(value, path),
        )


class AutoTextParser(GDocParser[AutoText]):
    def parse(self, data: JsonValue, *, path: str = "$") -> AutoText:
        value = object_value(data, path)
        return AutoText(
            auto_text_type=literal_value(
                required_field(value, "type", path),
                ("TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"),
                field_path(path, "type"),
            ),
            text_style=_optional_text_style(value, path),
        )


class ColumnBreakParser(GDocParser[ColumnBreak]):
    def parse(self, data: JsonValue, *, path: str = "$") -> ColumnBreak:
        value = object_value(data, path)
        return ColumnBreak(text_style=_optional_text_style(value, path))


class DateElementParser(GDocParser[DateElement]):
    def parse(self, data: JsonValue, *, path: str = "$") -> DateElement:
        value = object_value(data, path)
        properties = optional_object_field(value, "dateElementProperties", path)
        properties_path = field_path(path, "dateElementProperties")
        return DateElement(
            date_id=string_value(
                required_field(value, "dateId", path), field_path(path, "dateId")
            ),
            date_format=(
                UNSET
                if isinstance(properties, UnsetType)
                else optional_literal_field(
                    properties,
                    "dateFormat",
                    (
                        "DATE_FORMAT_UNSPECIFIED",
                        "DATE_FORMAT_CUSTOM",
                        "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
                        "DATE_FORMAT_MONTH_DAY_FULL",
                        "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
                        "DATE_FORMAT_ISO8601",
                    ),
                    properties_path,
                )
            ),
            display_text=_optional_nested_string(
                properties, "displayText", properties_path
            ),
            locale=_optional_nested_string(properties, "locale", properties_path),
            time_format=(
                UNSET
                if isinstance(properties, UnsetType)
                else optional_literal_field(
                    properties,
                    "timeFormat",
                    (
                        "TIME_FORMAT_UNSPECIFIED",
                        "TIME_FORMAT_DISABLED",
                        "TIME_FORMAT_HOUR_MINUTE",
                        "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
                    ),
                    properties_path,
                )
            ),
            time_zone_id=_optional_nested_string(
                properties, "timeZoneId", properties_path
            ),
            timestamp=_optional_nested_string(properties, "timestamp", properties_path),
            text_style=_optional_text_style(value, path),
        )


class EquationParser(GDocParser[Equation]):
    def parse(self, data: JsonValue, *, path: str = "$") -> Equation:
        object_value(data, path)
        return Equation()


class FootnoteReferenceParser(GDocParser[FootnoteReference]):
    def parse(self, data: JsonValue, *, path: str = "$") -> FootnoteReference:
        value = object_value(data, path)
        return FootnoteReference(
            footnote_id=string_value(
                required_field(value, "footnoteId", path),
                field_path(path, "footnoteId"),
            ),
            footnote_number=string_value(
                required_field(value, "footnoteNumber", path),
                field_path(path, "footnoteNumber"),
            ),
            text_style=_optional_text_style(value, path),
        )


class HorizontalRuleParser(GDocParser[HorizontalRule]):
    def parse(self, data: JsonValue, *, path: str = "$") -> HorizontalRule:
        value = object_value(data, path)
        return HorizontalRule(text_style=_optional_text_style(value, path))


class InlineObjectReferenceParser(GDocParser[InlineObjectReference]):
    def parse(self, data: JsonValue, *, path: str = "$") -> InlineObjectReference:
        value = object_value(data, path)
        return InlineObjectReference(
            inline_object_id=string_value(
                required_field(value, "inlineObjectId", path),
                field_path(path, "inlineObjectId"),
            ),
            text_style=_optional_text_style(value, path),
        )


class PageBreakParser(GDocParser[PageBreak]):
    def parse(self, data: JsonValue, *, path: str = "$") -> PageBreak:
        value = object_value(data, path)
        return PageBreak(text_style=_optional_text_style(value, path))


class PersonReferenceParser(GDocParser[PersonReference]):
    def parse(self, data: JsonValue, *, path: str = "$") -> PersonReference:
        value = object_value(data, path)
        properties = optional_object_field(value, "personProperties", path)
        properties_path = field_path(path, "personProperties")
        return PersonReference(
            person_id=string_value(
                required_field(value, "personId", path), field_path(path, "personId")
            ),
            email=_optional_nested_string(properties, "email", properties_path),
            name=_optional_nested_string(properties, "name", properties_path),
            text_style=_optional_text_style(value, path),
        )


class RichLinkParser(GDocParser[RichLink]):
    def parse(self, data: JsonValue, *, path: str = "$") -> RichLink:
        value = object_value(data, path)
        properties_path = field_path(path, "richLinkProperties")
        properties = object_value(
            required_field(value, "richLinkProperties", path), properties_path
        )
        return RichLink(
            rich_link_id=string_value(
                required_field(value, "richLinkId", path),
                field_path(path, "richLinkId"),
            ),
            uri=string_value(
                required_field(properties, "uri", properties_path),
                field_path(properties_path, "uri"),
            ),
            title=optional_string_field(properties, "title", properties_path),
            mime_type=optional_string_field(properties, "mimeType", properties_path),
            text_style=_optional_text_style(value, path),
        )


class ParagraphParser(GDocParser[Paragraph]):
    _element_keys = (
        "textRun",
        "autoText",
        "columnBreak",
        "dateElement",
        "equation",
        "footnoteReference",
        "horizontalRule",
        "inlineObjectElement",
        "pageBreak",
        "person",
        "richLink",
    )

    def parse(self, data: JsonValue, *, path: str = "$") -> Paragraph:
        value = object_value(data, path)
        return Paragraph(
            elements=self._parse_elements(value, path),
            style=(
                ParagraphStyle.gdoc_parser.parse(
                    value["paragraphStyle"],
                    path=field_path(path, "paragraphStyle"),
                )
                if "paragraphStyle" in value
                else UNSET
            ),
            bullet=(
                Bullet.gdoc_parser.parse(
                    value["bullet"], path=field_path(path, "bullet")
                )
                if "bullet" in value
                else UNSET
            ),
            positioned_object_ids=self._parse_positioned_object_ids(value, path),
        )

    def _parse_elements(self, value: JsonObject, path: str) -> list[ParagraphElement]:
        if "elements" not in value:
            return []
        elements_path = field_path(path, "elements")
        elements = array_value(value["elements"], elements_path)
        return [
            self._parse_element(element, index_path(elements_path, index))
            for index, element in enumerate(elements)
        ]

    def _parse_element(self, data: JsonValue, path: str) -> ParagraphElement:
        wrapper = object_value(data, path)
        present = [key for key in self._element_keys if key in wrapper]
        if len(present) != 1:
            raise GDocParseError(
                path, "expected exactly one supported paragraph element"
            )
        key = present[0]
        inner = wrapper[key]
        inner_path = field_path(path, key)
        if key == "textRun":
            return TextRun.gdoc_parser.parse(inner, path=inner_path)
        if key == "autoText":
            return AutoText.gdoc_parser.parse(inner, path=inner_path)
        if key == "columnBreak":
            return ColumnBreak.gdoc_parser.parse(inner, path=inner_path)
        if key == "dateElement":
            return DateElement.gdoc_parser.parse(inner, path=inner_path)
        if key == "equation":
            return Equation.gdoc_parser.parse(inner, path=inner_path)
        if key == "footnoteReference":
            return FootnoteReference.gdoc_parser.parse(inner, path=inner_path)
        if key == "horizontalRule":
            return HorizontalRule.gdoc_parser.parse(inner, path=inner_path)
        if key == "inlineObjectElement":
            return InlineObjectReference.gdoc_parser.parse(inner, path=inner_path)
        if key == "pageBreak":
            return PageBreak.gdoc_parser.parse(inner, path=inner_path)
        if key == "person":
            return PersonReference.gdoc_parser.parse(inner, path=inner_path)
        return RichLink.gdoc_parser.parse(inner, path=inner_path)

    @staticmethod
    def _parse_positioned_object_ids(
        value: JsonObject, path: str
    ) -> list[str] | UnsetType:
        if "positionedObjectIds" not in value:
            return UNSET
        ids_path = field_path(path, "positionedObjectIds")
        ids = array_value(value["positionedObjectIds"], ids_path)
        return [
            string_value(item, index_path(ids_path, index))
            for index, item in enumerate(ids)
        ]


class NamedStyleParser(GDocParser[NamedStyle]):
    def parse(self, data: JsonValue, *, path: str = "$") -> NamedStyle:
        value = object_value(data, path)
        return NamedStyle(
            named_style_type=literal_value(
                required_field(value, "namedStyleType", path),
                (
                    "NAMED_STYLE_TYPE_UNSPECIFIED",
                    "NORMAL_TEXT",
                    "TITLE",
                    "SUBTITLE",
                    "HEADING_1",
                    "HEADING_2",
                    "HEADING_3",
                    "HEADING_4",
                    "HEADING_5",
                    "HEADING_6",
                ),
                field_path(path, "namedStyleType"),
            ),
            text_style=_optional_text_style(value, path),
            paragraph_style=(
                ParagraphStyle.gdoc_parser.parse(
                    value["paragraphStyle"],
                    path=field_path(path, "paragraphStyle"),
                )
                if "paragraphStyle" in value
                else UNSET
            ),
        )


def _optional_text_style(value: JsonObject, path: str) -> TextStyle | UnsetType:
    if "textStyle" not in value:
        return UNSET
    return TextStyle.gdoc_parser.parse(
        value["textStyle"], path=field_path(path, "textStyle")
    )


def _optional_nested_string(
    value: JsonObject | UnsetType, key: str, path: str
) -> str | UnsetType:
    if isinstance(value, UnsetType):
        return UNSET
    return optional_string_field(value, key, path)


def _parse_dimension(value: JsonValue, path: str) -> Dimension:
    return Dimension.gdoc_parser.parse(value, path=path)


UrlLink.gdoc_parser = UrlLinkParser()
TabLink.gdoc_parser = TabLinkParser()
BookmarkLink.gdoc_parser = BookmarkLinkParser()
HeadingLink.gdoc_parser = HeadingLinkParser()
TextStyle.gdoc_parser = TextStyleParser()
Bullet.gdoc_parser = BulletParser()
ParagraphBorder.gdoc_parser = ParagraphBorderParser()
TabStop.gdoc_parser = TabStopParser()
ParagraphStyle.gdoc_parser = ParagraphStyleParser()
TextRun.gdoc_parser = TextRunParser()
AutoText.gdoc_parser = AutoTextParser()
ColumnBreak.gdoc_parser = ColumnBreakParser()
DateElement.gdoc_parser = DateElementParser()
Equation.gdoc_parser = EquationParser()
FootnoteReference.gdoc_parser = FootnoteReferenceParser()
HorizontalRule.gdoc_parser = HorizontalRuleParser()
InlineObjectReference.gdoc_parser = InlineObjectReferenceParser()
PageBreak.gdoc_parser = PageBreakParser()
PersonReference.gdoc_parser = PersonReferenceParser()
RichLink.gdoc_parser = RichLinkParser()
Paragraph.gdoc_parser = ParagraphParser()
NamedStyle.gdoc_parser = NamedStyleParser()
