from gdocs_patch.models import Color, Dimension
from gdocs_patch.parsers.base import color_parser, dimension_parser


def test_dimension_parser_normalizes_proto_defaults() -> None:
    assert dimension_parser.parse({}) == Dimension()
    assert dimension_parser.parse(
        {"magnitude": 12, "unit": "PT", "ignored": True}
    ) == Dimension(magnitude=12.0, unit="PT")


def test_color_parser_absorbs_rgb_color() -> None:
    assert color_parser.parse(
        {"rgbColor": {"red": 0.25, "green": 0.5, "blue": 1}}
    ) == Color(red=0.25, green=0.5, blue=1.0)
