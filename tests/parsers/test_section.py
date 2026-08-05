from gdocs_patch.models import Dimension
from gdocs_patch.models.section import SectionBreak, SectionColumn, SectionStyle


def test_parses_section_column() -> None:
    assert SectionColumn.gdoc_parser.parse(
        {
            "width": {"magnitude": 240, "unit": "PT"},
            "paddingEnd": {"magnitude": 12, "unit": "PT"},
        }
    ) == SectionColumn(
        width=Dimension(magnitude=240, unit="PT"),
        padding_end=Dimension(magnitude=12, unit="PT"),
    )


def test_parses_section_style() -> None:
    assert SectionStyle.gdoc_parser.parse(
        {
            "columnProperties": [
                {
                    "width": {"magnitude": 240, "unit": "PT"},
                    "paddingEnd": {"magnitude": 12, "unit": "PT"},
                },
                {
                    "width": {"magnitude": 228, "unit": "PT"},
                    "paddingEnd": {"magnitude": 0, "unit": "PT"},
                },
            ],
            "columnSeparatorStyle": "BETWEEN_EACH_COLUMN",
            "contentDirection": "RIGHT_TO_LEFT",
            "sectionType": "NEXT_PAGE",
            "defaultHeaderId": "header-default",
            "defaultFooterId": "footer-default",
            "evenPageHeaderId": "header-even",
            "evenPageFooterId": "footer-even",
            "firstPageHeaderId": "header-first",
            "firstPageFooterId": "footer-first",
            "useFirstPageHeaderFooter": True,
            "flipPageOrientation": False,
            "pageNumberStart": 7,
            "marginTop": {"magnitude": 72, "unit": "PT"},
            "marginBottom": {"magnitude": 73, "unit": "PT"},
            "marginLeft": {"magnitude": 74, "unit": "PT"},
            "marginRight": {"magnitude": 75, "unit": "PT"},
            "marginHeader": {"magnitude": 36, "unit": "PT"},
            "marginFooter": {"magnitude": 37, "unit": "PT"},
        }
    ) == SectionStyle(
        columns=[
            SectionColumn(
                width=Dimension(magnitude=240, unit="PT"),
                padding_end=Dimension(magnitude=12, unit="PT"),
            ),
            SectionColumn(
                width=Dimension(magnitude=228, unit="PT"),
                padding_end=Dimension(magnitude=0, unit="PT"),
            ),
        ],
        column_separator_style="BETWEEN_EACH_COLUMN",
        content_direction="RIGHT_TO_LEFT",
        section_type="NEXT_PAGE",
        default_header_id="header-default",
        default_footer_id="footer-default",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_first_page_header_footer=True,
        flip_page_orientation=False,
        page_number_start=7,
        margin_top=Dimension(magnitude=72, unit="PT"),
        margin_bottom=Dimension(magnitude=73, unit="PT"),
        margin_left=Dimension(magnitude=74, unit="PT"),
        margin_right=Dimension(magnitude=75, unit="PT"),
        margin_header=Dimension(magnitude=36, unit="PT"),
        margin_footer=Dimension(magnitude=37, unit="PT"),
    )


def test_parses_section_break_and_ignores_indices_and_suggestions() -> None:
    assert SectionBreak.gdoc_parser.parse(
        {
            "startIndex": 10,
            "endIndex": 11,
            "suggestedInsertionIds": ["suggestion-1"],
            "suggestedDeletionIds": ["suggestion-2"],
            "suggestedSectionStyleChanges": {"suggestion-3": {}},
            "sectionStyle": {"sectionType": "CONTINUOUS"},
        }
    ) == SectionBreak(style=SectionStyle(section_type="CONTINUOUS"))
