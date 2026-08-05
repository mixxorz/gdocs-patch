from typing import Any

from gdocs_patch.models.base import UNSET, Color, Dimension
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

from .base import GDocParser


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
        weighted_font_family = data.get("weightedFontFamily", {})
        link = UNSET
        if "link" in data:
            wrapper = data["link"]
            if "url" in wrapper:
                link = UrlLink.gdoc_parser.parse(wrapper["url"])
            elif "tabId" in wrapper:
                link = TabLink.gdoc_parser.parse(wrapper["tabId"])
            elif "bookmark" in wrapper:
                link = BookmarkLink.gdoc_parser.parse(wrapper["bookmark"])
            elif "heading" in wrapper:
                link = HeadingLink.gdoc_parser.parse(wrapper["heading"])
            elif "bookmarkId" in wrapper:
                link = BookmarkLink(bookmark_id=wrapper["bookmarkId"])
            else:
                link = HeadingLink(heading_id=wrapper["headingId"])
        return TextStyle(
            bold=data.get("bold", UNSET),
            italic=data.get("italic", UNSET),
            underline=data.get("underline", UNSET),
            strikethrough=data.get("strikethrough", UNSET),
            small_caps=data.get("smallCaps", UNSET),
            baseline_offset=data.get("baselineOffset", UNSET),
            font_size=(
                Dimension.gdoc_parser.parse(data["fontSize"])
                if "fontSize" in data
                else UNSET
            ),
            font_family=weighted_font_family.get("fontFamily", UNSET),
            font_weight=weighted_font_family.get("weight", UNSET),
            foreground_color=(
                None
                if data.get("foregroundColor", UNSET) == {}
                else (
                    Color.gdoc_parser.parse(data["foregroundColor"]["color"])
                    if "foregroundColor" in data
                    else UNSET
                )
            ),
            background_color=(
                None
                if data.get("backgroundColor", UNSET) == {}
                else (
                    Color.gdoc_parser.parse(data["backgroundColor"]["color"])
                    if "backgroundColor" in data
                    else UNSET
                )
            ),
            link=link,
        )


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
            color=(
                None
                if data["color"] == {}
                else Color.gdoc_parser.parse(data["color"]["color"])
            ),
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
            space_above=(
                Dimension.gdoc_parser.parse(data["spaceAbove"])
                if "spaceAbove" in data
                else UNSET
            ),
            space_below=(
                Dimension.gdoc_parser.parse(data["spaceBelow"])
                if "spaceBelow" in data
                else UNSET
            ),
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
            indent_end=(
                Dimension.gdoc_parser.parse(data["indentEnd"])
                if "indentEnd" in data
                else UNSET
            ),
            keep_lines_together=data.get("keepLinesTogether", UNSET),
            keep_with_next=data.get("keepWithNext", UNSET),
            avoid_widow_and_orphan=data.get("avoidWidowAndOrphan", UNSET),
            page_break_before=data.get("pageBreakBefore", UNSET),
            heading_id=data.get("headingId", UNSET),
            border_between=(
                ParagraphBorder.gdoc_parser.parse(data["borderBetween"])
                if "borderBetween" in data
                else UNSET
            ),
            border_top=(
                ParagraphBorder.gdoc_parser.parse(data["borderTop"])
                if "borderTop" in data
                else UNSET
            ),
            border_bottom=(
                ParagraphBorder.gdoc_parser.parse(data["borderBottom"])
                if "borderBottom" in data
                else UNSET
            ),
            border_left=(
                ParagraphBorder.gdoc_parser.parse(data["borderLeft"])
                if "borderLeft" in data
                else UNSET
            ),
            border_right=(
                ParagraphBorder.gdoc_parser.parse(data["borderRight"])
                if "borderRight" in data
                else UNSET
            ),
            shading_color=(
                None
                if data.get("shading", {}).get("backgroundColor", UNSET) == {}
                else (
                    Color.gdoc_parser.parse(data["shading"]["backgroundColor"]["color"])
                    if "shading" in data and "backgroundColor" in data["shading"]
                    else UNSET
                )
            ),
            tab_stops=(
                [TabStop.gdoc_parser.parse(item) for item in data["tabStops"]]
                if "tabStops" in data
                else UNSET
            ),
        )


class TextRunParser(GDocParser[TextRun]):
    def parse(self, data: Any) -> TextRun:
        return TextRun(
            content=data["content"],
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class AutoTextParser(GDocParser[AutoText]):
    def parse(self, data: Any) -> AutoText:
        return AutoText(
            auto_text_type=data["type"],
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class ColumnBreakParser(GDocParser[ColumnBreak]):
    def parse(self, data: Any) -> ColumnBreak:
        return ColumnBreak(
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            )
        )


class DateElementParser(GDocParser[DateElement]):
    def parse(self, data: Any) -> DateElement:
        properties = data.get("dateElementProperties", {})
        return DateElement(
            date_id=data["dateId"],
            date_format=properties.get("dateFormat", UNSET),
            display_text=properties.get("displayText", UNSET),
            locale=properties.get("locale", UNSET),
            time_format=properties.get("timeFormat", UNSET),
            time_zone_id=properties.get("timeZoneId", UNSET),
            timestamp=properties.get("timestamp", UNSET),
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class EquationParser(GDocParser[Equation]):
    def parse(self, data: Any) -> Equation:
        return Equation()


class FootnoteReferenceParser(GDocParser[FootnoteReference]):
    def parse(self, data: Any) -> FootnoteReference:
        return FootnoteReference(
            footnote_id=data["footnoteId"],
            footnote_number=data["footnoteNumber"],
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class HorizontalRuleParser(GDocParser[HorizontalRule]):
    def parse(self, data: Any) -> HorizontalRule:
        return HorizontalRule(
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            )
        )


class InlineObjectReferenceParser(GDocParser[InlineObjectReference]):
    def parse(self, data: Any) -> InlineObjectReference:
        return InlineObjectReference(
            inline_object_id=data["inlineObjectId"],
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class PageBreakParser(GDocParser[PageBreak]):
    def parse(self, data: Any) -> PageBreak:
        return PageBreak(
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            )
        )


class PersonReferenceParser(GDocParser[PersonReference]):
    def parse(self, data: Any) -> PersonReference:
        properties = data.get("personProperties", {})
        return PersonReference(
            person_id=data["personId"],
            email=properties.get("email", UNSET),
            name=properties.get("name", UNSET),
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class RichLinkParser(GDocParser[RichLink]):
    def parse(self, data: Any) -> RichLink:
        properties = data["richLinkProperties"]
        return RichLink(
            rich_link_id=data["richLinkId"],
            uri=properties["uri"],
            title=properties.get("title", UNSET),
            mime_type=properties.get("mimeType", UNSET),
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
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
            text_style=(
                TextStyle.gdoc_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
            paragraph_style=(
                ParagraphStyle.gdoc_parser.parse(data["paragraphStyle"])
                if "paragraphStyle" in data
                else UNSET
            ),
        )


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
