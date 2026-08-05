import pytest

from gdocs_patch.models import Color, Dimension
from gdocs_patch.models.paragraph import (
    BookmarkLink,
    Bullet,
    HeadingLink,
    ParagraphBorder,
    ParagraphStyle,
    TabLink,
    TabStop,
    TextStyle,
    UrlLink,
)
from gdocs_patch.parsers import GDocParser, JsonValue

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

CASES: list[tuple[GDocParser[object], JsonValue, object]] = [
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
]


@pytest.mark.parametrize(("parser", "payload", "expected"), CASES)
def test_parses_paragraph_presentation_model(
    parser: GDocParser[object], payload: JsonValue, expected: object
) -> None:
    assert parser.parse(payload) == expected


def test_text_style_normalizes_deprecated_bookmark_link() -> None:
    assert TextStyle.gdoc_parser.parse({"link": {"bookmarkId": "legacy"}}) == TextStyle(
        link=BookmarkLink(bookmark_id="legacy")
    )
