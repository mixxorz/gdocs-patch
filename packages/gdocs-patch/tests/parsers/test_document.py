import json
from pathlib import Path

from gdocs_patch.models import (
    Body,
    Color,
    Dimension,
    Document,
    DocumentStyle,
    DocumentTab,
    ListDefinition,
    ListLevel,
    NamedStyle,
    Paragraph,
    Segment,
    Tab,
    Table,
    TableCell,
    TableOfContents,
    TableRow,
)
from gdocs_patch.parsers import document_parser
from gdocs_patch.parsers.document import (
    document_style_parser,
    document_tab_parser,
    segment_parser,
    tab_parser,
)
from gdocs_patch.parsers.table import table_of_contents_parser

from .maximal_document import expected_maximal_document


def test_parses_document_style() -> None:
    decoded = {
        "background": {"color": {"color": {"rgbColor": {"red": 0.1}}}},
        "documentFormat": {"documentMode": "PAGES"},
        "pageSize": {
            "height": {"magnitude": 11, "unit": "PT"},
            "width": {"magnitude": 8.5, "unit": "PT"},
        },
        "marginTop": {"magnitude": 1, "unit": "PT"},
        "marginBottom": {"magnitude": 2, "unit": "PT"},
        "marginLeft": {"magnitude": 3, "unit": "PT"},
        "marginRight": {"magnitude": 4, "unit": "PT"},
        "marginHeader": {"magnitude": 5, "unit": "PT"},
        "marginFooter": {"magnitude": 6, "unit": "PT"},
        "defaultHeaderId": "header-default",
        "defaultFooterId": "footer-default",
        "evenPageHeaderId": "header-even",
        "evenPageFooterId": "footer-even",
        "firstPageHeaderId": "header-first",
        "firstPageFooterId": "footer-first",
        "useEvenPageHeaderFooter": True,
        "useFirstPageHeaderFooter": False,
        "useCustomHeaderFooterMargins": True,
        "flipPageOrientation": False,
        "pageNumberStart": 3,
    }

    assert document_style_parser.parse(decoded) == DocumentStyle(
        background_color=Color(red=0.1),
        document_mode="PAGES",
        page_width=Dimension(magnitude=8.5, unit="PT"),
        page_height=Dimension(magnitude=11, unit="PT"),
        margin_top=Dimension(magnitude=1, unit="PT"),
        margin_bottom=Dimension(magnitude=2, unit="PT"),
        margin_left=Dimension(magnitude=3, unit="PT"),
        margin_right=Dimension(magnitude=4, unit="PT"),
        margin_header=Dimension(magnitude=5, unit="PT"),
        margin_footer=Dimension(magnitude=6, unit="PT"),
        default_header_id="header-default",
        default_footer_id="footer-default",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_even_page_header_footer=True,
        use_first_page_header_footer=False,
        use_custom_header_footer_margins=True,
        flip_page_orientation=False,
        page_number_start=3,
    )


def test_parses_segment() -> None:
    decoded = {
        "headerId": "header-1",
        "content": [{"paragraph": {"elements": []}}],
    }

    assert segment_parser.parse(decoded) == Segment(
        segment_id="header-1", content=[Paragraph(elements=[])]
    )


def test_parses_table_of_contents() -> None:
    decoded = {
        "content": [
            {"paragraph": {"elements": []}},
            {
                "table": {
                    "tableRows": [
                        {
                            "startIndex": 1,
                            "endIndex": 4,
                            "tableCells": [{"startIndex": 2, "endIndex": 4}],
                        }
                    ]
                }
            },
        ]
    }

    assert table_of_contents_parser.parse(decoded) == TableOfContents(
        content=[
            Paragraph(elements=[]),
            Table(
                table_key="table-c9935b85",
                rows=[
                    TableRow(
                        row_key="row-7a670ae8",
                        cells=[
                            TableCell(
                                cell_key="cell-63af18a5",
                                content=[],
                            )
                        ],
                    )
                ],
            ),
        ]
    )


def test_parses_document_tab() -> None:
    decoded = {
        "body": {"content": [{"paragraph": {}}]},
        "headers": {"header-1": {"headerId": "header-1"}},
        "footers": {"footer-1": {"footerId": "footer-1"}},
        "footnotes": {"footnote-1": {"footnoteId": "footnote-1"}},
        "documentStyle": {},
        "namedStyles": {"styles": [{"namedStyleType": "NORMAL_TEXT"}]},
        "lists": {
            "list-1": {
                "listProperties": {
                    "nestingLevels": [{"glyphFormat": "%0", "glyphType": "DECIMAL"}]
                }
            }
        },
    }

    assert document_tab_parser.parse(decoded) == DocumentTab(
        body=Body(content=[Paragraph(elements=[])]),
        headers={"header-1": Segment(segment_id="header-1", content=[])},
        footers={"footer-1": Segment(segment_id="footer-1", content=[])},
        footnotes={"footnote-1": Segment(segment_id="footnote-1", content=[])},
        document_style=DocumentStyle(),
        named_styles=[NamedStyle(named_style_type="NORMAL_TEXT")],
        lists={
            "list-1": ListDefinition(
                levels=[ListLevel(glyph_format="%0", glyph_type="DECIMAL")]
            )
        },
    )


def test_parses_tab_recursively() -> None:
    decoded = {
        "tabProperties": {
            "tabId": "tab-root",
            "title": "Root",
            "index": 0,
            "nestingLevel": 1,
            "parentTabId": "tab-parent",
            "iconEmoji": "📄",
        },
        "documentTab": {},
        "childTabs": [
            {
                "tabProperties": {
                    "tabId": "tab-child",
                    "title": "Child",
                    "index": 1,
                }
            }
        ],
    }

    assert tab_parser.parse(decoded) == Tab(
        tab_id="tab-root",
        title="Root",
        index=0,
        nesting_level=1,
        parent_tab_id="tab-parent",
        icon_emoji="📄",
        content=DocumentTab(),
        children=[
            Tab(tab_id="tab-child", title="Child", index=1, children=[]),
        ],
    )


def test_parses_document_and_ignores_legacy_fields() -> None:
    decoded = {
        "documentId": "doc-1",
        "title": "Example",
        "revisionId": "revision-1",
        "suggestionsViewMode": "SUGGESTIONS_INLINE",
        "tabs": [{"tabProperties": {"tabId": "tab-1", "title": "Main", "index": 0}}],
        "body": {"content": []},
        "headers": {},
        "footers": {},
        "footnotes": {},
        "documentStyle": {},
        "namedStyles": {},
        "lists": {},
        "namedRanges": {},
        "inlineObjects": {},
        "positionedObjects": {},
    }

    assert document_parser.parse(decoded) == Document(
        document_id="doc-1",
        title="Example",
        revision_id="revision-1",
        suggestions_view_mode="SUGGESTIONS_INLINE",
        tabs=[Tab(tab_id="tab-1", title="Main", index=0, children=[])],
    )


def test_parses_maximal_document_response() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "maximal_document.json"
    decoded = json.loads(fixture_path.read_text())

    assert document_parser.parse(decoded) == expected_maximal_document()


def test_maximal_document_indices_match_fixture() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "maximal_document.json"
    decoded = json.loads(fixture_path.read_text())
    document = document_parser.parse(decoded)
    tab = document.tabs[0].content
    assert isinstance(tab, DocumentTab)
    assert isinstance(tab.body, Body)
    body = tab.body

    paragraph = body.content[0]
    assert isinstance(paragraph, Paragraph)
    assert (paragraph.start_index, paragraph.end_index, paragraph.utf16_width) == (
        0,
        14,
        14,
    )
    assert (
        paragraph.elements[0].start_index,
        paragraph.elements[0].end_index,
        paragraph.elements[0].utf16_width,
    ) == (0, 4, 4)
    assert (
        paragraph.elements[1].start_index,
        paragraph.elements[1].end_index,
        paragraph.elements[1].utf16_width,
    ) == (4, 5, 1)
    assert (
        paragraph.elements[2].start_index,
        paragraph.elements[2].end_index,
        paragraph.elements[2].utf16_width,
    ) == (5, 6, 1)
    assert (
        paragraph.elements[3].start_index,
        paragraph.elements[3].end_index,
        paragraph.elements[3].utf16_width,
    ) == (6, 7, 1)
    assert (
        paragraph.elements[4].start_index,
        paragraph.elements[4].end_index,
        paragraph.elements[4].utf16_width,
    ) == (7, 8, 1)
    assert (
        paragraph.elements[5].start_index,
        paragraph.elements[5].end_index,
        paragraph.elements[5].utf16_width,
    ) == (8, 9, 1)
    assert (
        paragraph.elements[6].start_index,
        paragraph.elements[6].end_index,
        paragraph.elements[6].utf16_width,
    ) == (9, 10, 1)
    assert (
        paragraph.elements[7].start_index,
        paragraph.elements[7].end_index,
        paragraph.elements[7].utf16_width,
    ) == (10, 11, 1)
    assert (
        paragraph.elements[8].start_index,
        paragraph.elements[8].end_index,
        paragraph.elements[8].utf16_width,
    ) == (11, 12, 1)
    assert (
        paragraph.elements[9].start_index,
        paragraph.elements[9].end_index,
        paragraph.elements[9].utf16_width,
    ) == (12, 13, 1)
    assert (
        paragraph.elements[10].start_index,
        paragraph.elements[10].end_index,
        paragraph.elements[10].utf16_width,
    ) == (13, 14, 1)

    section_break = body.content[1]
    assert (
        section_break.start_index,
        section_break.end_index,
        section_break.utf16_width,
    ) == (14, 15, 1)

    table = body.content[2]
    assert isinstance(table, Table)
    assert (table.start_index, table.end_index, table.utf16_width) == (15, 40, 25)
    row = table.rows[0]
    assert (row.start_index, row.end_index, row.utf16_width) == (16, 39, 23)
    first_cell = row.cells[0]
    assert (
        first_cell.start_index,
        first_cell.end_index,
        first_cell.utf16_width,
    ) == (17, 38, 21)
    cell_paragraph = first_cell.content[0]
    assert isinstance(cell_paragraph, Paragraph)
    assert (
        cell_paragraph.start_index,
        cell_paragraph.end_index,
        cell_paragraph.utf16_width,
    ) == (18, 22, 4)
    assert (
        cell_paragraph.elements[0].start_index,
        cell_paragraph.elements[0].end_index,
        cell_paragraph.elements[0].utf16_width,
    ) == (18, 22, 4)

    nested_table = first_cell.content[1]
    assert isinstance(nested_table, Table)
    assert (
        nested_table.start_index,
        nested_table.end_index,
        nested_table.utf16_width,
    ) == (22, 37, 15)
    nested_row = nested_table.rows[0]
    assert (
        nested_row.start_index,
        nested_row.end_index,
        nested_row.utf16_width,
    ) == (23, 36, 13)
    nested_cell = nested_row.cells[0]
    assert (
        nested_cell.start_index,
        nested_cell.end_index,
        nested_cell.utf16_width,
    ) == (24, 36, 12)
    nested_paragraph = nested_cell.content[0]
    assert isinstance(nested_paragraph, Paragraph)
    assert (
        nested_paragraph.start_index,
        nested_paragraph.end_index,
        nested_paragraph.utf16_width,
    ) == (25, 36, 11)
    assert (
        nested_paragraph.elements[0].start_index,
        nested_paragraph.elements[0].end_index,
        nested_paragraph.elements[0].utf16_width,
    ) == (25, 36, 11)

    cell_toc = first_cell.content[2]
    assert isinstance(cell_toc, TableOfContents)
    assert (cell_toc.start_index, cell_toc.end_index, cell_toc.utf16_width) == (
        37,
        38,
        1,
    )
    cell_toc_paragraph = cell_toc.content[0]
    assert (
        cell_toc_paragraph.start_index,
        cell_toc_paragraph.end_index,
        cell_toc_paragraph.utf16_width,
    ) == (38, 38, 0)

    second_cell = row.cells[1]
    assert (
        second_cell.start_index,
        second_cell.end_index,
        second_cell.utf16_width,
    ) == (38, 39, 1)
    second_cell_paragraph = second_cell.content[0]
    assert (
        second_cell_paragraph.start_index,
        second_cell_paragraph.end_index,
        second_cell_paragraph.utf16_width,
    ) == (39, 39, 0)

    toc = body.content[3]
    assert isinstance(toc, TableOfContents)
    assert (toc.start_index, toc.end_index, toc.utf16_width) == (40, 41, 1)
    toc_paragraph = toc.content[0]
    assert (
        toc_paragraph.start_index,
        toc_paragraph.end_index,
        toc_paragraph.utf16_width,
    ) == (41, 41, 0)

    assert isinstance(tab.headers, dict)
    header_paragraph = tab.headers["header-map-key"].content[0]
    assert (
        header_paragraph.start_index,
        header_paragraph.end_index,
        header_paragraph.utf16_width,
    ) == (0, 0, 0)
    assert isinstance(tab.footnotes, dict)
    footnote_paragraph = tab.footnotes["footnote-1"].content[0]
    assert (
        footnote_paragraph.start_index,
        footnote_paragraph.end_index,
        footnote_paragraph.utf16_width,
    ) == (0, 0, 0)

    assert body.parent is None
    assert paragraph.parent is body
    assert paragraph.elements[0].parent is paragraph
    assert row.parent is table
    assert first_cell.parent is row
    assert cell_paragraph.parent is first_cell
