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
    TableOfContents,
)
from gdocs_patch.parsers import document_parser
from gdocs_patch.parsers.document import (
    document_style_parser,
    document_tab_parser,
    segment_parser,
    tab_parser,
)
from gdocs_patch.parsers.table import table_of_contents_parser
from tests.parsers.maximal_document import expected_maximal_document


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
            {"table": {"tableRows": []}},
        ]
    }

    assert table_of_contents_parser.parse(decoded) == TableOfContents(
        content=[Paragraph(elements=[]), Table(rows=[])]
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
    raw_tab = decoded["tabs"][0]["documentTab"]
    tab = document.tabs[0].content

    def compare_node(raw: dict[str, object], node: object) -> tuple[int, int]:
        assert node.start_index == raw["startIndex"]
        assert node.end_index == raw["endIndex"]
        assert node.utf16_width == raw["endIndex"] - raw["startIndex"]
        return 1, 2

    def compare_content(
        raw_content: list[dict[str, object]], content: list[object]
    ) -> tuple[int, int]:
        compared_nodes = 0
        compared_index_values = 0
        assert len(content) == len(raw_content)
        for raw, node in zip(raw_content, content, strict=True):
            nodes, values = compare_node(raw, node)
            compared_nodes += nodes
            compared_index_values += values

            if "paragraph" in raw:
                raw_elements = raw["paragraph"].get("elements", [])
                assert isinstance(node, Paragraph)
                for raw_element, element in zip(
                    raw_elements, node.elements, strict=True
                ):
                    nodes, values = compare_node(raw_element, element)
                    compared_nodes += nodes
                    compared_index_values += values
            elif "table" in raw:
                assert isinstance(node, Table)
                raw_rows = raw["table"].get("tableRows", [])
                for raw_row, row in zip(raw_rows, node.rows, strict=True):
                    nodes, values = compare_node(raw_row, row)
                    compared_nodes += nodes
                    compared_index_values += values
                    raw_cells = raw_row.get("tableCells", [])
                    for raw_cell, cell in zip(raw_cells, row.cells, strict=True):
                        nodes, values = compare_node(raw_cell, cell)
                        compared_nodes += nodes
                        compared_index_values += values
                        nodes, values = compare_content(
                            raw_cell.get("content", []), cell.content
                        )
                        compared_nodes += nodes
                        compared_index_values += values
            elif "tableOfContents" in raw:
                assert isinstance(node, TableOfContents)
                nodes, values = compare_content(
                    raw["tableOfContents"].get("content", []), node.content
                )
                compared_nodes += nodes
                compared_index_values += values

        return compared_nodes, compared_index_values

    compared_nodes, compared_index_values = compare_content(
        raw_tab["body"]["content"], tab.body.content
    )
    for collection_name in ("headers", "footers", "footnotes"):
        raw_segments = raw_tab.get(collection_name, {})
        segments = getattr(tab, collection_name)
        for key, raw_segment in raw_segments.items():
            nodes, values = compare_content(
                raw_segment.get("content", []), segments[key].content
            )
            compared_nodes += nodes
            compared_index_values += values

    assert compared_nodes == 31
    assert compared_index_values == 62

    body = tab.body
    paragraph = body.content[0]
    table = body.content[2]
    assert body.parent is None
    assert body.content[0].parent is body
    assert paragraph.elements[0].parent is paragraph
    assert table.rows[0].parent is table
    assert table.rows[0].cells[0].parent is table.rows[0]
    assert table.rows[0].cells[0].content[0].parent is table.rows[0].cells[0]
