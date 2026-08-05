from typing import Any

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

from .base import GDocParser, parse_optional_color


class UrlLinkParser(GDocParser[UrlLink]):
    def parse(self, data: Any) -> UrlLink:
        return UrlLink(url=data)


class TabLinkParser(GDocParser[TabLink]):
    def parse(self, data: Any) -> TabLink:
        return TabLink(tab_id=data)


class BookmarkLinkParser(GDocParser[BookmarkLink]):
    def parse(self, data: Any) -> BookmarkLink:
        return BookmarkLink(bookmark_id=data["id"], tab_id=data.get("tabId", UNSET))


class HeadingLinkParser(GDocParser[HeadingLink]):
    def parse(self, data: Any) -> HeadingLink:
        return HeadingLink(heading_id=data["id"], tab_id=data.get("tabId", UNSET))


class TextStyleParser(GDocParser[TextStyle]):
    def parse(self, data: Any) -> TextStyle:
        weighted_font_family = data.get("weightedFontFamily", UNSET)
        return TextStyle(
            bold=data.get("bold", UNSET),
            italic=data.get("italic", UNSET),
            underline=data.get("underline", UNSET),
            strikethrough=data.get("strikethrough", UNSET),
            small_caps=data.get("smallCaps", UNSET),
            baseline_offset=data.get("baselineOffset", UNSET),
            font_size=self._optional_dimension(data, "fontSize"),
            font_family=(
                UNSET
                if isinstance(weighted_font_family, UnsetType)
                else weighted_font_family.get("fontFamily", UNSET)
            ),
            font_weight=(
                UNSET
                if isinstance(weighted_font_family, UnsetType)
                else weighted_font_family.get("weight", UNSET)
            ),
            foreground_color=self._optional_color(data, "foregroundColor"),
            background_color=self._optional_color(data, "backgroundColor"),
            link=self._optional_link(data),
        )

    @staticmethod
    def _optional_dimension(data: Any, key: str) -> Dimension | UnsetType:
        if key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])

    @staticmethod
    def _optional_color(data: Any, key: str) -> Color | None | UnsetType:
        if key not in data:
            return UNSET
        return parse_optional_color(data[key])

    @staticmethod
    def _optional_link(data: Any) -> Link | UnsetType:
        if "link" not in data:
            return UNSET
        wrapper = data["link"]
        if "url" in wrapper:
            return UrlLink.gdoc_parser.parse(wrapper["url"])
        if "tabId" in wrapper:
            return TabLink.gdoc_parser.parse(wrapper["tabId"])
        if "bookmark" in wrapper:
            return BookmarkLink.gdoc_parser.parse(wrapper["bookmark"])
        if "heading" in wrapper:
            return HeadingLink.gdoc_parser.parse(wrapper["heading"])
        if "bookmarkId" in wrapper:
            return BookmarkLink(bookmark_id=wrapper["bookmarkId"])
        return HeadingLink(heading_id=wrapper["headingId"])


class BulletParser(GDocParser[Bullet]):
    def parse(self, data: Any) -> Bullet:
        return Bullet(
            list_id=data["listId"],
            nesting_level=data.get("nestingLevel", 0),
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class ParagraphBorderParser(GDocParser[ParagraphBorder]):
    def parse(self, data: Any) -> ParagraphBorder:
        return ParagraphBorder(
            color=parse_optional_color(data["color"]),
            width=Dimension.gdoc_parser.parse(data["width"]),
            padding=Dimension.gdoc_parser.parse(data["padding"]),
            dash_style=data["dashStyle"],
        )


class TabStopParser(GDocParser[TabStop]):
    def parse(self, data: Any) -> TabStop:
        return TabStop(
            offset=Dimension.gdoc_parser.parse(data["offset"]),
            alignment=data["alignment"],
        )


class ParagraphStyleParser(GDocParser[ParagraphStyle]):
    def parse(self, data: Any) -> ParagraphStyle:
        return ParagraphStyle(
            named_style_type=data.get("namedStyleType", UNSET),
            alignment=data.get("alignment", UNSET),
            direction=data.get("direction", UNSET),
            line_spacing=(
                float(data["lineSpacing"]) if "lineSpacing" in data else UNSET
            ),
            spacing_mode=data.get("spacingMode", UNSET),
            space_above=self._optional_dimension(data, "spaceAbove"),
            space_below=self._optional_dimension(data, "spaceBelow"),
            indent_first_line=self._optional_dimension(data, "indentFirstLine"),
            indent_start=self._optional_dimension(data, "indentStart"),
            indent_end=self._optional_dimension(data, "indentEnd"),
            keep_lines_together=data.get("keepLinesTogether", UNSET),
            keep_with_next=data.get("keepWithNext", UNSET),
            avoid_widow_and_orphan=data.get("avoidWidowAndOrphan", UNSET),
            page_break_before=data.get("pageBreakBefore", UNSET),
            heading_id=data.get("headingId", UNSET),
            border_between=self._optional_border(data, "borderBetween"),
            border_top=self._optional_border(data, "borderTop"),
            border_bottom=self._optional_border(data, "borderBottom"),
            border_left=self._optional_border(data, "borderLeft"),
            border_right=self._optional_border(data, "borderRight"),
            shading_color=self._optional_shading(data),
            tab_stops=(
                [TabStop.gdoc_parser.parse(item) for item in data["tabStops"]]
                if "tabStops" in data
                else UNSET
            ),
        )

    @staticmethod
    def _optional_dimension(data: Any, key: str) -> Dimension | UnsetType:
        if key not in data:
            return UNSET
        return Dimension.gdoc_parser.parse(data[key])

    @staticmethod
    def _optional_border(data: Any, key: str) -> ParagraphBorder | UnsetType:
        if key not in data:
            return UNSET
        return ParagraphBorder.gdoc_parser.parse(data[key])

    @staticmethod
    def _optional_shading(data: Any) -> Color | None | UnsetType:
        if "shading" not in data or "backgroundColor" not in data["shading"]:
            return UNSET
        return parse_optional_color(data["shading"]["backgroundColor"])


class TextRunParser(GDocParser[TextRun]):
    def parse(self, data: Any) -> TextRun:
        return TextRun(content=data["content"], text_style=_optional_text_style(data))


class AutoTextParser(GDocParser[AutoText]):
    def parse(self, data: Any) -> AutoText:
        return AutoText(
            auto_text_type=data["type"], text_style=_optional_text_style(data)
        )


class ColumnBreakParser(GDocParser[ColumnBreak]):
    def parse(self, data: Any) -> ColumnBreak:
        return ColumnBreak(text_style=_optional_text_style(data))


class DateElementParser(GDocParser[DateElement]):
    def parse(self, data: Any) -> DateElement:
        properties = data.get("dateElementProperties", UNSET)
        return DateElement(
            date_id=data["dateId"],
            date_format=self._optional_property(properties, "dateFormat"),
            display_text=self._optional_property(properties, "displayText"),
            locale=self._optional_property(properties, "locale"),
            time_format=self._optional_property(properties, "timeFormat"),
            time_zone_id=self._optional_property(properties, "timeZoneId"),
            timestamp=self._optional_property(properties, "timestamp"),
            text_style=_optional_text_style(data),
        )

    @staticmethod
    def _optional_property(data: Any | UnsetType, key: str) -> Any | UnsetType:
        if isinstance(data, UnsetType):
            return UNSET
        return data.get(key, UNSET)


class EquationParser(GDocParser[Equation]):
    def parse(self, data: Any) -> Equation:
        return Equation()


class FootnoteReferenceParser(GDocParser[FootnoteReference]):
    def parse(self, data: Any) -> FootnoteReference:
        return FootnoteReference(
            footnote_id=data["footnoteId"],
            footnote_number=data["footnoteNumber"],
            text_style=_optional_text_style(data),
        )


class HorizontalRuleParser(GDocParser[HorizontalRule]):
    def parse(self, data: Any) -> HorizontalRule:
        return HorizontalRule(text_style=_optional_text_style(data))


class InlineObjectReferenceParser(GDocParser[InlineObjectReference]):
    def parse(self, data: Any) -> InlineObjectReference:
        return InlineObjectReference(
            inline_object_id=data["inlineObjectId"],
            text_style=_optional_text_style(data),
        )


class PageBreakParser(GDocParser[PageBreak]):
    def parse(self, data: Any) -> PageBreak:
        return PageBreak(text_style=_optional_text_style(data))


class PersonReferenceParser(GDocParser[PersonReference]):
    def parse(self, data: Any) -> PersonReference:
        properties = data.get("personProperties", UNSET)
        return PersonReference(
            person_id=data["personId"],
            email=self._optional_property(properties, "email"),
            name=self._optional_property(properties, "name"),
            text_style=_optional_text_style(data),
        )

    @staticmethod
    def _optional_property(data: Any | UnsetType, key: str) -> Any | UnsetType:
        if isinstance(data, UnsetType):
            return UNSET
        return data.get(key, UNSET)


class RichLinkParser(GDocParser[RichLink]):
    def parse(self, data: Any) -> RichLink:
        properties = data["richLinkProperties"]
        return RichLink(
            rich_link_id=data["richLinkId"],
            uri=properties["uri"],
            title=properties.get("title", UNSET),
            mime_type=properties.get("mimeType", UNSET),
            text_style=_optional_text_style(data),
        )


class ParagraphParser(GDocParser[Paragraph]):
    def parse(self, data: Any) -> Paragraph:
        return Paragraph(
            elements=[
                self._parse_element(element) for element in data.get("elements", [])
            ],
            style=(
                ParagraphStyle.gdoc_parser.parse(data["paragraphStyle"])
                if "paragraphStyle" in data
                else UNSET
            ),
            bullet=(
                Bullet.gdoc_parser.parse(data["bullet"]) if "bullet" in data else UNSET
            ),
            positioned_object_ids=(
                [object_id for object_id in data["positionedObjectIds"]]
                if "positionedObjectIds" in data
                else UNSET
            ),
        )

    @staticmethod
    def _parse_element(data: Any) -> ParagraphElement:
        if "textRun" in data:
            return TextRun.gdoc_parser.parse(data["textRun"])
        if "autoText" in data:
            return AutoText.gdoc_parser.parse(data["autoText"])
        if "columnBreak" in data:
            return ColumnBreak.gdoc_parser.parse(data["columnBreak"])
        if "dateElement" in data:
            return DateElement.gdoc_parser.parse(data["dateElement"])
        if "equation" in data:
            return Equation.gdoc_parser.parse(data["equation"])
        if "footnoteReference" in data:
            return FootnoteReference.gdoc_parser.parse(data["footnoteReference"])
        if "horizontalRule" in data:
            return HorizontalRule.gdoc_parser.parse(data["horizontalRule"])
        if "inlineObjectElement" in data:
            return InlineObjectReference.gdoc_parser.parse(data["inlineObjectElement"])
        if "pageBreak" in data:
            return PageBreak.gdoc_parser.parse(data["pageBreak"])
        if "person" in data:
            return PersonReference.gdoc_parser.parse(data["person"])
        return RichLink.gdoc_parser.parse(data["richLink"])


class NamedStyleParser(GDocParser[NamedStyle]):
    def parse(self, data: Any) -> NamedStyle:
        return NamedStyle(
            named_style_type=data["namedStyleType"],
            text_style=_optional_text_style(data),
            paragraph_style=(
                ParagraphStyle.gdoc_parser.parse(data["paragraphStyle"])
                if "paragraphStyle" in data
                else UNSET
            ),
        )


def _optional_text_style(data: Any) -> TextStyle | UnsetType:
    if "textStyle" not in data:
        return UNSET
    return TextStyle.gdoc_parser.parse(data["textStyle"])


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
