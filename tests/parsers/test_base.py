import pytest

from gdocs_patch.models import Color, Dimension
from gdocs_patch.parsers import GDocParseError


def test_dimension_parser_normalizes_proto_defaults() -> None:
    assert Dimension.gdoc_parser.parse({}) == Dimension()
    assert Dimension.gdoc_parser.parse(
        {"magnitude": 12, "unit": "PT", "ignored": True}
    ) == Dimension(magnitude=12.0, unit="PT")


def test_color_parser_absorbs_rgb_color() -> None:
    assert Color.gdoc_parser.parse(
        {"rgbColor": {"red": 0.25, "green": 0.5, "blue": 1}}
    ) == Color(red=0.25, green=0.5, blue=1.0)


def test_constructor_error_is_wrapped_and_chained() -> None:
    with pytest.raises(GDocParseError) as caught:
        Color.gdoc_parser.parse({"rgbColor": {"red": 2}})

    assert isinstance(caught.value.__cause__, ValueError)
