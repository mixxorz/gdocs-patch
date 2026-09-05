import pytest

from gdocs_patch.models.list import ListLevel


def test_list_level_accepts_a_symbol_glyph() -> None:
    level = ListLevel(glyph_format="%0", glyph_symbol="●")

    assert level.alignment == "BULLET_ALIGNMENT_UNSPECIFIED"
    assert level.start_number == 0


def test_list_level_accepts_a_numbered_glyph() -> None:
    level = ListLevel(glyph_format="%0.", glyph_type="DECIMAL")

    assert level.glyph_type == "DECIMAL"


def test_list_level_rejects_missing_glyph_representation() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one of glyph_type and glyph_symbol must be set",
    ):
        ListLevel(glyph_format="%0")


def test_list_level_rejects_both_glyph_representations() -> None:
    with pytest.raises(
        ValueError,
        match="exactly one of glyph_type and glyph_symbol must be set",
    ):
        ListLevel(
            glyph_format="%0",
            glyph_type="DECIMAL",
            glyph_symbol="●",
        )
