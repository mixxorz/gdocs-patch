import pytest

from gdocs_patch.models.document import Body, Segment, TableOfContents
from gdocs_patch.models.paragraph import Equation, Paragraph, TextRun
from gdocs_patch.models.section import SectionBreak, SectionStyle
from gdocs_patch.models.table import Table, TableCell, TableRow


def test_body_indices_follow_utf16_widths_and_current_sibling_order() -> None:
    section = SectionBreak(style=SectionStyle())
    first = TextRun(content="A🌍")
    second = Equation()
    paragraph = Paragraph(elements=[first, second])
    following = Paragraph(elements=[TextRun(content="Z")])
    body = Body(content=[section, paragraph, following])

    assert body.parent is None
    assert (section.start_index, section.end_index) == (0, 1)
    assert (paragraph.start_index, paragraph.end_index) == (1, 5)
    assert (first.start_index, first.end_index) == (1, 4)
    assert (second.start_index, second.end_index) == (4, 5)
    assert following.start_index == 5

    paragraph.elements.reverse()

    assert second.start_index == 1
    assert first.start_index == 2
    assert following.start_index == 5

    first.content = "A"

    assert paragraph.end_index == 3
    assert following.start_index == 3


def test_each_segment_is_an_independent_zero_based_root() -> None:
    paragraph = Paragraph(elements=[TextRun(content="Header")])
    segment = Segment(segment_id="header", content=[paragraph])

    assert segment.parent is None
    assert paragraph.start_index == 0
    assert paragraph.end_index == 6


def test_detached_node_has_width_but_no_indices() -> None:
    run = TextRun(content="🌍")

    assert run.utf16_width == 2
    with pytest.raises(ValueError, match="not attached"):
        _ = run.start_index
    with pytest.raises(ValueError, match="not attached"):
        _ = run.end_index


def test_unpaired_surrogate_has_one_utf16_code_unit() -> None:
    assert TextRun(content="\ud800").utf16_width == 1


def test_semantic_tree_constructors_retain_supplied_children_lists() -> None:
    paragraph = Paragraph(elements=[])
    cell_content = [paragraph]
    cell = TableCell(content=cell_content)
    cells = [cell]
    row = TableRow(cells=cells)
    rows = [row]
    table = Table(rows=rows)
    toc_content = [Paragraph(elements=[])]
    toc = TableOfContents(content=toc_content)
    body_content = [table, toc]
    body = Body(content=body_content)
    segment_content = [Paragraph(elements=[])]
    segment = Segment(segment_id="header", content=segment_content)

    assert cell.content is cell_content
    assert row.cells is cells
    assert table.rows is rows
    assert toc.content is toc_content
    assert body.content is body_content
    assert segment.content is segment_content
    assert paragraph.parent is cell
    assert cell.parent is row
    assert row.parent is table
    assert table.parent is body
    assert toc.parent is body
    assert segment_content[0].parent is segment

    added = Paragraph(elements=[])
    segment_content.append(added)

    assert segment.content[-1] is added
    assert added.parent is None


def test_table_boundaries_and_nested_content_are_derived_from_children() -> None:
    cell_paragraph = Paragraph(elements=[TextRun(content="x\n")])
    first_cell = TableCell(content=[cell_paragraph])
    second_cell = TableCell(content=[Paragraph(elements=[])])
    row = TableRow(cells=[first_cell, second_cell])
    table = Table(rows=[row])
    toc_paragraph = Paragraph(elements=[TextRun(content="T\n")])
    toc = TableOfContents(content=[toc_paragraph])
    following = Paragraph(elements=[TextRun(content="Z")])
    Body(content=[table, toc, following])

    assert (table.start_index, table.end_index) == (0, 7)
    assert (row.start_index, row.end_index) == (1, 6)
    assert (first_cell.start_index, first_cell.end_index) == (2, 5)
    assert cell_paragraph.start_index == 3
    assert (second_cell.start_index, second_cell.end_index) == (5, 6)
    assert (toc.start_index, toc.end_index) == (7, 10)
    assert toc_paragraph.start_index == 8
    assert following.start_index == 10
