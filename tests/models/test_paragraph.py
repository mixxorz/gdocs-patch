from gdocs_patch.models.paragraph import Bullet, Paragraph, TextRun


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_retains_supplied_elements_list() -> None:
    initial = TextRun(content="Initial")
    elements = [initial]

    paragraph = Paragraph(elements=elements)
    added_directly = TextRun(content="Added directly")
    elements.append(added_directly)

    assert paragraph.elements is elements
    assert paragraph.children is elements
    assert paragraph.elements == [initial, added_directly]
    assert initial.parent is paragraph
    assert added_directly.parent is None


def test_paragraph_add_child_sets_parent() -> None:
    paragraph = Paragraph(elements=[])
    run = TextRun(content="Added later")

    paragraph.add_child(run)

    assert paragraph.elements == [run]
    assert run.parent is paragraph
