from gdocs_patch.models.paragraph import Bullet, Paragraph, TextRun


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_reflects_mutations_to_supplied_elements_list() -> None:
    elements = []
    paragraph = Paragraph(elements=elements)

    elements.append(TextRun(content="Added later"))

    assert paragraph.elements == [TextRun(content="Added later")]
