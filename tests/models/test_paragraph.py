from gdocs_patch.models.paragraph import Bullet, Paragraph, TextRun


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_adds_paragraph_elements_as_children() -> None:
    paragraph = Paragraph(elements=[])
    run = TextRun(content="Added later")

    paragraph.add_child(run)

    assert paragraph.elements == [run]
    assert paragraph.elements is paragraph.children
    assert run.parent is paragraph
