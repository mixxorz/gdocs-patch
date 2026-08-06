from gdocs_patch.compiler.edit_script import (
    ApplyParagraphStyle,
    ApplyTextStyle,
    CreateParagraphBullets,
    DeleteContent,
    DeleteParagraphBullets,
    EditScript,
    InsertText,
)
from gdocs_patch.compiler.lowering import lower_edit_script
from gdocs_patch.models import (
    UNSET,
    BookmarkLink,
    BulletPreset,
    Color,
    Dimension,
    ParagraphBorder,
    ParagraphStyle,
    TabStop,
    TextStyle,
)


def test_lowers_content_paragraph_and_bullet_edits() -> None:
    edit_script = EditScript(
        edits=[
            InsertText(index=4, text="new"),
            DeleteContent(start_index=8, end_index=11),
            ApplyTextStyle(
                start_index=1,
                end_index=4,
                text_style=TextStyle(
                    bold=True,
                    italic=False,
                    font_size=Dimension(magnitude=12, unit="PT"),
                    font_family="Roboto",
                    font_weight=500,
                    foreground_color=Color(red=0.1, green=0.2, blue=0.3),
                    background_color=None,
                    link=BookmarkLink(
                        bookmark_id="bookmark-1",
                        tab_id="tab-linked",
                    ),
                ),
            ),
            ApplyTextStyle(start_index=4, end_index=5, text_style=UNSET),
            ApplyParagraphStyle(
                start_index=0,
                end_index=12,
                paragraph_style=ParagraphStyle(
                    named_style_type="HEADING_2",
                    alignment="CENTER",
                    space_above=Dimension(magnitude=6, unit="PT"),
                    border_bottom=ParagraphBorder(
                        color=Color(red=0.4, green=0.5, blue=0.6),
                        width=Dimension(magnitude=1, unit="PT"),
                        padding=Dimension(magnitude=2, unit="PT"),
                        dash_style="SOLID",
                    ),
                    shading_color=None,
                    heading_id="read-only-heading",
                    tab_stops=[
                        TabStop(
                            offset=Dimension(magnitude=36, unit="PT"),
                            alignment="START",
                        )
                    ],
                ),
            ),
            ApplyParagraphStyle(
                start_index=12,
                end_index=13,
                paragraph_style=UNSET,
            ),
            CreateParagraphBullets(
                start_index=13,
                end_index=20,
                bullet_preset=BulletPreset(
                    preset="BULLET_DISC_CIRCLE_SQUARE",
                    nesting_level=2,
                ),
            ),
            DeleteParagraphBullets(start_index=20, end_index=27),
        ]
    )

    assert lower_edit_script(edit_script=edit_script, tab_id="tab-1") == [
        {
            "insertText": {
                "location": {"index": 4, "tabId": "tab-1"},
                "text": "new",
            }
        },
        {
            "deleteContentRange": {
                "range": {
                    "startIndex": 8,
                    "endIndex": 11,
                    "tabId": "tab-1",
                }
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": 1,
                    "endIndex": 4,
                    "tabId": "tab-1",
                },
                "textStyle": {
                    "bold": True,
                    "italic": False,
                    "fontSize": {"magnitude": 12, "unit": "PT"},
                    "weightedFontFamily": {
                        "fontFamily": "Roboto",
                        "weight": 500,
                    },
                    "foregroundColor": {
                        "color": {"rgbColor": {"red": 0.1, "green": 0.2, "blue": 0.3}}
                    },
                    "backgroundColor": {},
                    "link": {
                        "bookmarkId": "bookmark-1",
                        "tabId": "tab-linked",
                    },
                },
                "fields": (
                    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,"
                    "fontSize,weightedFontFamily,foregroundColor,backgroundColor,link"
                ),
            }
        },
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": 4,
                    "endIndex": 5,
                    "tabId": "tab-1",
                },
                "textStyle": {},
                "fields": (
                    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,"
                    "fontSize,weightedFontFamily,foregroundColor,backgroundColor,link"
                ),
            }
        },
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": 0,
                    "endIndex": 12,
                    "tabId": "tab-1",
                },
                "paragraphStyle": {
                    "namedStyleType": "HEADING_2",
                    "alignment": "CENTER",
                    "spaceAbove": {"magnitude": 6, "unit": "PT"},
                    "borderBottom": {
                        "color": {
                            "color": {
                                "rgbColor": {
                                    "red": 0.4,
                                    "green": 0.5,
                                    "blue": 0.6,
                                }
                            }
                        },
                        "width": {"magnitude": 1, "unit": "PT"},
                        "padding": {"magnitude": 2, "unit": "PT"},
                        "dashStyle": "SOLID",
                    },
                    "shading": {"backgroundColor": {}},
                },
                "fields": (
                    "namedStyleType,alignment,direction,lineSpacing,spacingMode,"
                    "spaceAbove,spaceBelow,indentFirstLine,indentStart,indentEnd,"
                    "keepLinesTogether,keepWithNext,avoidWidowAndOrphan,"
                    "pageBreakBefore,borderBetween,borderTop,borderBottom,borderLeft,"
                    "borderRight,shading"
                ),
            }
        },
        {
            "updateParagraphStyle": {
                "range": {
                    "startIndex": 12,
                    "endIndex": 13,
                    "tabId": "tab-1",
                },
                "paragraphStyle": {},
                "fields": (
                    "namedStyleType,alignment,direction,lineSpacing,spacingMode,"
                    "spaceAbove,spaceBelow,indentFirstLine,indentStart,indentEnd,"
                    "keepLinesTogether,keepWithNext,avoidWidowAndOrphan,"
                    "pageBreakBefore,borderBetween,borderTop,borderBottom,borderLeft,"
                    "borderRight,shading"
                ),
            }
        },
        {
            "insertText": {
                "location": {"index": 13, "tabId": "tab-1"},
                "text": "\t\t",
            }
        },
        {
            "createParagraphBullets": {
                "range": {
                    "startIndex": 13,
                    "endIndex": 22,
                    "tabId": "tab-1",
                },
                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
            }
        },
        {
            "deleteParagraphBullets": {
                "range": {
                    "startIndex": 20,
                    "endIndex": 27,
                    "tabId": "tab-1",
                }
            }
        },
    ]


def test_lowers_body_and_segment_locations() -> None:
    edit_script = EditScript(edits=[InsertText(index=3, text="header")])

    assert lower_edit_script(
        edit_script=edit_script,
        tab_id="tab-2",
        segment_id="header-1",
    ) == [
        {
            "insertText": {
                "location": {
                    "index": 3,
                    "tabId": "tab-2",
                    "segmentId": "header-1",
                },
                "text": "header",
            }
        }
    ]
    assert lower_edit_script(edit_script=edit_script, tab_id="tab-2") == [
        {
            "insertText": {
                "location": {
                    "index": 3,
                    "tabId": "tab-2",
                },
                "text": "header",
            }
        }
    ]
