from typing import Any

import pytest

from gdocs_patch.models import UNSET, Color, Dimension
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
    ParagraphStyle,
    PersonReference,
    RichLink,
    TabLink,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
)
from gdocs_patch.parsers import GDocParser

DIMENSION = {"magnitude": 12, "unit": "PT"}
OPAQUE_COLOR = {"color": {"rgbColor": {"red": 0.25, "green": 0.5, "blue": 1}}}
BORDER = {
    "color": OPAQUE_COLOR,
    "width": DIMENSION,
    "padding": {"magnitude": 2, "unit": "PT"},
    "dashStyle": "SOLID",
}
EXPECTED_BORDER = ParagraphBorder(
    color=Color(red=0.25, green=0.5, blue=1),
    width=Dimension(magnitude=12, unit="PT"),
    padding=Dimension(magnitude=2, unit="PT"),
    dash_style="SOLID",
)

CASES: list[tuple[GDocParser[object], Any, object]] = [
    (UrlLink.gdoc_parser, "https://example.test", UrlLink(url="https://example.test")),
    (TabLink.gdoc_parser, "tab-2", TabLink(tab_id="tab-2")),
    (
        BookmarkLink.gdoc_parser,
        {"id": "bookmark-1", "tabId": "tab-2"},
        BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-2"),
    ),
    (
        HeadingLink.gdoc_parser,
        {"id": "heading-1", "tabId": "tab-2"},
        HeadingLink(heading_id="heading-1", tab_id="tab-2"),
    ),
    (
        TextStyle.gdoc_parser,
        {
            "bold": True,
            "italic": False,
            "underline": True,
            "strikethrough": False,
            "smallCaps": True,
            "baselineOffset": "SUPERSCRIPT",
            "fontSize": DIMENSION,
            "weightedFontFamily": {"fontFamily": "Inter", "weight": 600},
            "foregroundColor": OPAQUE_COLOR,
            "backgroundColor": {},
            "link": {"url": "https://example.test"},
        },
        TextStyle(
            bold=True,
            italic=False,
            underline=True,
            strikethrough=False,
            small_caps=True,
            baseline_offset="SUPERSCRIPT",
            font_size=Dimension(magnitude=12, unit="PT"),
            font_family="Inter",
            font_weight=600,
            foreground_color=Color(red=0.25, green=0.5, blue=1),
            background_color=None,
            link=UrlLink(url="https://example.test"),
        ),
    ),
    (
        Bullet.gdoc_parser,
        {"listId": "list-1", "textStyle": {"bold": True}},
        Bullet(list_id="list-1", nesting_level=0, text_style=TextStyle(bold=True)),
    ),
    (ParagraphBorder.gdoc_parser, BORDER, EXPECTED_BORDER),
    (
        TabStop.gdoc_parser,
        {"offset": DIMENSION, "alignment": "CENTER"},
        TabStop(offset=Dimension(magnitude=12, unit="PT"), alignment="CENTER"),
    ),
    (
        ParagraphStyle.gdoc_parser,
        {
            "namedStyleType": "HEADING_2",
            "alignment": "JUSTIFIED",
            "direction": "RIGHT_TO_LEFT",
            "lineSpacing": 115,
            "spacingMode": "NEVER_COLLAPSE",
            "spaceAbove": DIMENSION,
            "spaceBelow": DIMENSION,
            "indentFirstLine": DIMENSION,
            "indentStart": DIMENSION,
            "indentEnd": DIMENSION,
            "keepLinesTogether": True,
            "keepWithNext": False,
            "avoidWidowAndOrphan": True,
            "pageBreakBefore": False,
            "headingId": "heading-1",
            "borderBetween": BORDER,
            "borderTop": BORDER,
            "borderBottom": BORDER,
            "borderLeft": BORDER,
            "borderRight": BORDER,
            "shading": {"backgroundColor": OPAQUE_COLOR},
            "tabStops": [
                {"offset": DIMENSION, "alignment": "START"},
                {"offset": {"magnitude": 24, "unit": "PT"}, "alignment": "END"},
            ],
        },
        ParagraphStyle(
            named_style_type="HEADING_2",
            alignment="JUSTIFIED",
            direction="RIGHT_TO_LEFT",
            line_spacing=115.0,
            spacing_mode="NEVER_COLLAPSE",
            space_above=Dimension(magnitude=12, unit="PT"),
            space_below=Dimension(magnitude=12, unit="PT"),
            indent_first_line=Dimension(magnitude=12, unit="PT"),
            indent_start=Dimension(magnitude=12, unit="PT"),
            indent_end=Dimension(magnitude=12, unit="PT"),
            keep_lines_together=True,
            keep_with_next=False,
            avoid_widow_and_orphan=True,
            page_break_before=False,
            heading_id="heading-1",
            border_between=EXPECTED_BORDER,
            border_top=EXPECTED_BORDER,
            border_bottom=EXPECTED_BORDER,
            border_left=EXPECTED_BORDER,
            border_right=EXPECTED_BORDER,
            shading_color=Color(red=0.25, green=0.5, blue=1),
            tab_stops=[
                TabStop(offset=Dimension(magnitude=12, unit="PT"), alignment="START"),
                TabStop(offset=Dimension(magnitude=24, unit="PT"), alignment="END"),
            ],
        ),
    ),
    (
        TextRun.gdoc_parser,
        {"content": "Hello", "textStyle": {"bold": True}},
        TextRun(content="Hello", text_style=TextStyle(bold=True)),
    ),
    (
        AutoText.gdoc_parser,
        {"type": "PAGE_NUMBER", "textStyle": {"italic": True}},
        AutoText(auto_text_type="PAGE_NUMBER", text_style=TextStyle(italic=True)),
    ),
    (
        ColumnBreak.gdoc_parser,
        {"textStyle": {"underline": True}},
        ColumnBreak(text_style=TextStyle(underline=True)),
    ),
    (
        DateElement.gdoc_parser,
        {
            "dateId": "date-1",
            "dateElementProperties": {
                "dateFormat": "DATE_FORMAT_ISO8601",
                "displayText": "2025-03-08",
                "locale": "en-US",
                "timeFormat": "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
                "timeZoneId": "America/New_York",
                "timestamp": "2025-03-08T10:30:00Z",
            },
            "textStyle": {"bold": True},
        },
        DateElement(
            date_id="date-1",
            date_format="DATE_FORMAT_ISO8601",
            display_text="2025-03-08",
            locale="en-US",
            time_format="TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
            time_zone_id="America/New_York",
            timestamp="2025-03-08T10:30:00Z",
            text_style=TextStyle(bold=True),
        ),
    ),
    (
        Equation.gdoc_parser,
        {"suggestedInsertionIds": ["suggestion-1"]},
        Equation(),
    ),
    (
        FootnoteReference.gdoc_parser,
        {
            "footnoteId": "footnote-1",
            "footnoteNumber": "1",
            "textStyle": {"italic": True},
        },
        FootnoteReference(
            footnote_id="footnote-1",
            footnote_number="1",
            text_style=TextStyle(italic=True),
        ),
    ),
    (
        HorizontalRule.gdoc_parser,
        {"textStyle": {"bold": True}},
        HorizontalRule(text_style=TextStyle(bold=True)),
    ),
    (
        InlineObjectReference.gdoc_parser,
        {"inlineObjectId": "inline-1", "textStyle": {"underline": True}},
        InlineObjectReference(
            inline_object_id="inline-1",
            text_style=TextStyle(underline=True),
        ),
    ),
    (
        PageBreak.gdoc_parser,
        {"textStyle": {"smallCaps": True}},
        PageBreak(text_style=TextStyle(small_caps=True)),
    ),
    (
        PersonReference.gdoc_parser,
        {
            "personId": "person-1",
            "personProperties": {"email": "ada@example.test", "name": "Ada"},
            "textStyle": {"bold": True},
        },
        PersonReference(
            person_id="person-1",
            email="ada@example.test",
            name="Ada",
            text_style=TextStyle(bold=True),
        ),
    ),
    (
        RichLink.gdoc_parser,
        {
            "richLinkId": "rich-link-1",
            "richLinkProperties": {
                "uri": "https://example.test/resource",
                "title": "Resource",
                "mimeType": "text/html",
            },
            "textStyle": {"italic": True},
        },
        RichLink(
            rich_link_id="rich-link-1",
            uri="https://example.test/resource",
            title="Resource",
            mime_type="text/html",
            text_style=TextStyle(italic=True),
        ),
    ),
    (
        Paragraph.gdoc_parser,
        {
            "paragraphStyle": {"alignment": "CENTER"},
            "bullet": {"listId": "list-1"},
            "positionedObjectIds": ["positioned-1", "positioned-2"],
            "elements": [
                {
                    "startIndex": 1,
                    "endIndex": 2,
                    "suggestedInsertionIds": ["suggestion-1"],
                    "textRun": {"content": "Hello"},
                },
                {
                    "startIndex": 2,
                    "endIndex": 3,
                    "suggestedDeletionIds": ["suggestion-2"],
                    "autoText": {"type": "PAGE_COUNT"},
                },
                {
                    "startIndex": 3,
                    "endIndex": 4,
                    "suggestedTextStyleChanges": {},
                    "columnBreak": {},
                },
                {
                    "startIndex": 4,
                    "endIndex": 5,
                    "suggestedInsertionIds": [],
                    "dateElement": {"dateId": "date-1"},
                },
                {
                    "startIndex": 5,
                    "endIndex": 6,
                    "suggestedDeletionIds": [],
                    "equation": {},
                },
                {
                    "startIndex": 6,
                    "endIndex": 7,
                    "suggestedTextStyleChanges": {},
                    "footnoteReference": {
                        "footnoteId": "footnote-1",
                        "footnoteNumber": "1",
                    },
                },
                {
                    "startIndex": 7,
                    "endIndex": 8,
                    "suggestedInsertionIds": [],
                    "horizontalRule": {},
                },
                {
                    "startIndex": 8,
                    "endIndex": 9,
                    "suggestedDeletionIds": [],
                    "inlineObjectElement": {"inlineObjectId": "inline-1"},
                },
                {
                    "startIndex": 9,
                    "endIndex": 10,
                    "suggestedTextStyleChanges": {},
                    "pageBreak": {},
                },
                {
                    "startIndex": 10,
                    "endIndex": 11,
                    "suggestedInsertionIds": [],
                    "person": {"personId": "person-1"},
                },
                {
                    "startIndex": 11,
                    "endIndex": 12,
                    "suggestedDeletionIds": [],
                    "richLink": {
                        "richLinkId": "rich-link-1",
                        "richLinkProperties": {"uri": "https://example.test"},
                    },
                },
            ],
        },
        Paragraph(
            style=ParagraphStyle(alignment="CENTER"),
            bullet=Bullet(list_id="list-1"),
            positioned_object_ids=["positioned-1", "positioned-2"],
            elements=[
                TextRun(content="Hello"),
                AutoText(auto_text_type="PAGE_COUNT"),
                ColumnBreak(),
                DateElement(date_id="date-1"),
                Equation(),
                FootnoteReference(footnote_id="footnote-1", footnote_number="1"),
                HorizontalRule(),
                InlineObjectReference(inline_object_id="inline-1"),
                PageBreak(),
                PersonReference(person_id="person-1"),
                RichLink(rich_link_id="rich-link-1", uri="https://example.test"),
            ],
        ),
    ),
    (
        NamedStyle.gdoc_parser,
        {
            "namedStyleType": "TITLE",
            "textStyle": {"bold": True},
            "paragraphStyle": {"alignment": "CENTER"},
        },
        NamedStyle(
            named_style_type="TITLE",
            text_style=TextStyle(bold=True),
            paragraph_style=ParagraphStyle(alignment="CENTER"),
        ),
    ),
]


@pytest.mark.parametrize(("parser", "payload", "expected"), CASES)
def test_parses_paragraph_presentation_model(
    parser: GDocParser[object], payload: Any, expected: object
) -> None:
    assert parser.parse(payload) == expected


def test_paragraph_copies_positioned_object_ids() -> None:
    positioned_object_ids = ["positioned-1"]

    paragraph = Paragraph.gdoc_parser.parse(
        {"positionedObjectIds": positioned_object_ids}
    )
    positioned_object_ids.append("positioned-2")

    assert paragraph.positioned_object_ids == ["positioned-1"]


def test_text_style_normalizes_deprecated_bookmark_link() -> None:
    assert TextStyle.gdoc_parser.parse({"link": {"bookmarkId": "legacy"}}) == TextStyle(
        link=BookmarkLink(bookmark_id="legacy")
    )


def test_paragraph_style_distinguishes_absent_and_transparent_shading_color() -> None:
    assert ParagraphStyle.gdoc_parser.parse({"shading": {}}) == ParagraphStyle(
        shading_color=UNSET
    )
    assert ParagraphStyle.gdoc_parser.parse(
        {"shading": {"backgroundColor": {}}}
    ) == ParagraphStyle(shading_color=None)
