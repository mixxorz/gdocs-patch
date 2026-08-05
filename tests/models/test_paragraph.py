from gdocs_patch.models.paragraph import Bullet, Paragraph, TextRun


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_constructor_sets_element_parent() -> None:
    run = TextRun(content="Initial")

    paragraph = Paragraph(elements=[run])

    assert paragraph.elements == [run]
    assert run.parent is paragraph


def test_paragraph_add_child_sets_parent() -> None:
    paragraph = Paragraph(elements=[])
    run = TextRun(content="Added later")

    paragraph.add_child(run)

    assert paragraph.elements == [run]
    assert run.parent is paragraph
