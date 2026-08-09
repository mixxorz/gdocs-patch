from gdocs_patch.models import (
    UNSET,
    Body,
    Dimension,
    Document,
    DocumentTab,
    InlineObjectReference,
    PageBreak,
    Paragraph,
    PersonReference,
    RichLink,
    SectionBreak,
    SectionStyle,
    Table,
    TableCellStyle,
    TableOfContents,
    TextRun,
    TreeNode,
)
from gdocs_patch.xhtml import deserialize_document, serialize_document
from tests.parsers.maximal_document import expected_maximal_document


def _prepend_leading_section(document: Document) -> None:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    body = content.body
    assert isinstance(body, Body)
    content.body = Body(content=[SectionBreak(style=SectionStyle()), *body.content])


def _normalize_paragraph_terminators(node: TreeNode) -> None:
    if isinstance(node, Paragraph) and not (
        node.elements
        and isinstance(node.elements[-1], TextRun)
        and node.elements[-1].content.endswith("\n")
    ):
        node.add_child(TextRun(content="\n"))
    for child in node.children:
        _normalize_paragraph_terminators(child)


def test_full_supported_document_has_normalized_stable_round_trip() -> None:
    input_document = expected_maximal_document()
    expected_document = expected_maximal_document()
    _prepend_leading_section(input_document)
    _prepend_leading_section(expected_document)

    content = expected_document.tabs[0].content
    assert isinstance(content, DocumentTab)
    body = content.body
    assert isinstance(body, Body)
    rich_paragraph = body.content[1]
    assert isinstance(rich_paragraph, Paragraph)
    for index in (7, 8, 9, 10):
        element = rich_paragraph.elements[index]
        assert isinstance(
            element,
            (InlineObjectReference, PageBreak, PersonReference, RichLink),
        )
        element.text_style = UNSET

    table = body.content[3]
    assert isinstance(table, Table)
    first_cell_style = table.rows[0].cells[0].style
    assert isinstance(first_cell_style, TableCellStyle)
    first_cell_style.padding_left = Dimension(magnitude=0, unit="PT")
    table.rows[0].cells[1].style = UNSET

    trees: list[TreeNode] = [body]
    for segments in (content.headers, content.footers, content.footnotes):
        if isinstance(segments, dict):
            trees.extend(segments.values())
    for tree in trees:
        _normalize_paragraph_terminators(tree)

    xhtml = serialize_document(input_document)
    actual = deserialize_document(xhtml)

    assert actual == expected_document
    assert serialize_document(actual) == xhtml

    actual_content = actual.tabs[0].content
    assert isinstance(actual_content, DocumentTab)
    actual_body = actual_content.body
    assert isinstance(actual_body, Body)
    paragraph = actual_body.content[1]
    assert isinstance(paragraph, Paragraph)
    actual_table = actual_body.content[3]
    assert isinstance(actual_table, Table)
    row = actual_table.rows[0]
    cell = row.cells[0]
    nested_table = cell.content[1]
    assert isinstance(nested_table, Table)
    nested_content = cell.content[2]
    assert isinstance(nested_content, TableOfContents)

    assert paragraph.parent is actual_body
    assert paragraph.elements[0].parent is paragraph
    assert actual_table.parent is actual_body
    assert row.parent is actual_table
    assert cell.parent is row
    assert nested_table.parent is cell
    assert nested_content.parent is cell
    assert nested_content.content[0].parent is nested_content
