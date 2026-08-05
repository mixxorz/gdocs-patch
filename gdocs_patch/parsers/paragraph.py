from typing import Any

from gdocs_patch.models.base import UNSET
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

from .base import GDocParser, color_parser, dimension_parser


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
                link = url_link_parser.parse(wrapper["url"])
            elif "tabId" in wrapper:
                link = tab_link_parser.parse(wrapper["tabId"])
            elif "bookmark" in wrapper:
                link = bookmark_link_parser.parse(wrapper["bookmark"])
            elif "heading" in wrapper:
                link = heading_link_parser.parse(wrapper["heading"])
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
                dimension_parser.parse(data["fontSize"])
                if "fontSize" in data
                else UNSET
            ),
            font_family=weighted_font_family.get("fontFamily", UNSET),
            font_weight=weighted_font_family.get("weight", UNSET),
            foreground_color=(
                None
                if data.get("foregroundColor", UNSET) == {}
                else (
                    color_parser.parse(data["foregroundColor"]["color"])
                    if "foregroundColor" in data
                    else UNSET
                )
            ),
            background_color=(
                None
                if data.get("backgroundColor", UNSET) == {}
                else (
                    color_parser.parse(data["backgroundColor"]["color"])
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
                text_style_parser.parse(data["textStyle"])
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
                else color_parser.parse(data["color"]["color"])
            ),
            width=dimension_parser.parse(data["width"]),
            padding=dimension_parser.parse(data["padding"]),
            dash_style=data["dashStyle"],
        )


class TabStopParser(GDocParser[TabStop]):
    def parse(self, data: Any) -> TabStop:
        return TabStop(
            offset=dimension_parser.parse(data["offset"]),
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
                dimension_parser.parse(data["spaceAbove"])
                if "spaceAbove" in data
                else UNSET
            ),
            space_below=(
                dimension_parser.parse(data["spaceBelow"])
                if "spaceBelow" in data
                else UNSET
            ),
            indent_first_line=(
                dimension_parser.parse(data["indentFirstLine"])
                if "indentFirstLine" in data
                else UNSET
            ),
            indent_start=(
                dimension_parser.parse(data["indentStart"])
                if "indentStart" in data
                else UNSET
            ),
            indent_end=(
                dimension_parser.parse(data["indentEnd"])
                if "indentEnd" in data
                else UNSET
            ),
            keep_lines_together=data.get("keepLinesTogether", UNSET),
            keep_with_next=data.get("keepWithNext", UNSET),
            avoid_widow_and_orphan=data.get("avoidWidowAndOrphan", UNSET),
            page_break_before=data.get("pageBreakBefore", UNSET),
            heading_id=data.get("headingId", UNSET),
            border_between=(
                paragraph_border_parser.parse(data["borderBetween"])
                if "borderBetween" in data
                else UNSET
            ),
            border_top=(
                paragraph_border_parser.parse(data["borderTop"])
                if "borderTop" in data
                else UNSET
            ),
            border_bottom=(
                paragraph_border_parser.parse(data["borderBottom"])
                if "borderBottom" in data
                else UNSET
            ),
            border_left=(
                paragraph_border_parser.parse(data["borderLeft"])
                if "borderLeft" in data
                else UNSET
            ),
            border_right=(
                paragraph_border_parser.parse(data["borderRight"])
                if "borderRight" in data
                else UNSET
            ),
            shading_color=(
                None
                if data.get("shading", {}).get("backgroundColor", UNSET) == {}
                else (
                    color_parser.parse(data["shading"]["backgroundColor"]["color"])
                    if "shading" in data and "backgroundColor" in data["shading"]
                    else UNSET
                )
            ),
            tab_stops=(
                [tab_stop_parser.parse(item) for item in data["tabStops"]]
                if "tabStops" in data
                else UNSET
            ),
        )


class TextRunParser(GDocParser[TextRun]):
    def parse(self, data: Any) -> TextRun:
        return TextRun(
            content=data["content"],
            text_style=(
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class AutoTextParser(GDocParser[AutoText]):
    def parse(self, data: Any) -> AutoText:
        return AutoText(
            auto_text_type=data["type"],
            text_style=(
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class ColumnBreakParser(GDocParser[ColumnBreak]):
    def parse(self, data: Any) -> ColumnBreak:
        return ColumnBreak(
            text_style=(
                text_style_parser.parse(data["textStyle"])
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
                text_style_parser.parse(data["textStyle"])
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
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class HorizontalRuleParser(GDocParser[HorizontalRule]):
    def parse(self, data: Any) -> HorizontalRule:
        return HorizontalRule(
            text_style=(
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            )
        )


class InlineObjectReferenceParser(GDocParser[InlineObjectReference]):
    def parse(self, data: Any) -> InlineObjectReference:
        return InlineObjectReference(
            inline_object_id=data["inlineObjectId"],
            text_style=(
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class PageBreakParser(GDocParser[PageBreak]):
    def parse(self, data: Any) -> PageBreak:
        return PageBreak(
            text_style=(
                text_style_parser.parse(data["textStyle"])
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
                text_style_parser.parse(data["textStyle"])
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
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
        )


class ParagraphParser(GDocParser[Paragraph]):
    def parse(self, data: Any) -> Paragraph:
        elements: list[ParagraphElement] = []
        for element in data.get("elements", []):
            if "textRun" in element:
                elements.append(text_run_parser.parse(element["textRun"]))
            elif "autoText" in element:
                elements.append(auto_text_parser.parse(element["autoText"]))
            elif "columnBreak" in element:
                elements.append(column_break_parser.parse(element["columnBreak"]))
            elif "dateElement" in element:
                elements.append(date_element_parser.parse(element["dateElement"]))
            elif "equation" in element:
                elements.append(equation_parser.parse(element["equation"]))
            elif "footnoteReference" in element:
                elements.append(
                    footnote_reference_parser.parse(element["footnoteReference"])
                )
            elif "horizontalRule" in element:
                elements.append(horizontal_rule_parser.parse(element["horizontalRule"]))
            elif "inlineObjectElement" in element:
                elements.append(
                    inline_object_reference_parser.parse(element["inlineObjectElement"])
                )
            elif "pageBreak" in element:
                elements.append(page_break_parser.parse(element["pageBreak"]))
            elif "person" in element:
                elements.append(person_reference_parser.parse(element["person"]))
            else:
                elements.append(rich_link_parser.parse(element["richLink"]))
        return Paragraph(
            elements=elements,
            style=(
                paragraph_style_parser.parse(data["paragraphStyle"])
                if "paragraphStyle" in data
                else UNSET
            ),
            bullet=(bullet_parser.parse(data["bullet"]) if "bullet" in data else UNSET),
            positioned_object_ids=(
                [object_id for object_id in data["positionedObjectIds"]]
                if "positionedObjectIds" in data
                else UNSET
            ),
        )


class NamedStyleParser(GDocParser[NamedStyle]):
    def parse(self, data: Any) -> NamedStyle:
        return NamedStyle(
            named_style_type=data["namedStyleType"],
            text_style=(
                text_style_parser.parse(data["textStyle"])
                if "textStyle" in data
                else UNSET
            ),
            paragraph_style=(
                paragraph_style_parser.parse(data["paragraphStyle"])
                if "paragraphStyle" in data
                else UNSET
            ),
        )


url_link_parser = UrlLinkParser()
tab_link_parser = TabLinkParser()
bookmark_link_parser = BookmarkLinkParser()
heading_link_parser = HeadingLinkParser()
text_style_parser = TextStyleParser()
bullet_parser = BulletParser()
paragraph_border_parser = ParagraphBorderParser()
tab_stop_parser = TabStopParser()
paragraph_style_parser = ParagraphStyleParser()
text_run_parser = TextRunParser()
auto_text_parser = AutoTextParser()
column_break_parser = ColumnBreakParser()
date_element_parser = DateElementParser()
equation_parser = EquationParser()
footnote_reference_parser = FootnoteReferenceParser()
horizontal_rule_parser = HorizontalRuleParser()
inline_object_reference_parser = InlineObjectReferenceParser()
page_break_parser = PageBreakParser()
person_reference_parser = PersonReferenceParser()
rich_link_parser = RichLinkParser()
paragraph_parser = ParagraphParser()
named_style_parser = NamedStyleParser()
