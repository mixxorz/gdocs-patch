import pytest

from gdocs_patch.models.document import Body, Segment
from gdocs_patch.models.paragraph import Equation, Paragraph, TextRun
from gdocs_patch.models.section import SectionBreak, SectionStyle


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
