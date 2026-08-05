from gdocs_patch.models.paragraph import Bullet, Paragraph


def test_bullet_defaults_to_top_level_nesting() -> None:
    bullet = Bullet(list_id="list-1")

    assert bullet.nesting_level == 0


def test_paragraph_retains_the_supplied_elements_collection() -> None:
    elements = []

    paragraph = Paragraph(elements=elements)

    assert paragraph.elements is elements
