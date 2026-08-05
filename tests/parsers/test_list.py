import gdocs_patch.parsers  # noqa: F401
from gdocs_patch.models import UNSET, Dimension
from gdocs_patch.models.list import ListDefinition, ListLevel
from gdocs_patch.models.paragraph import TextStyle


def test_parses_list_level_with_proto_defaults_and_optional_fields() -> None:
    assert ListLevel.gdoc_parser.parse(
        {
            "glyphFormat": "%0.",
            "glyphSymbol": "●",
            "indentFirstLine": {"magnitude": 18, "unit": "PT"},
            "indentStart": {"magnitude": 36, "unit": "PT"},
            "textStyle": {"bold": True},
        }
    ) == ListLevel(
        glyph_format="%0.",
        glyph_type=UNSET,
        glyph_symbol="●",
        alignment="BULLET_ALIGNMENT_UNSPECIFIED",
        indent_first_line=Dimension(magnitude=18, unit="PT"),
        indent_start=Dimension(magnitude=36, unit="PT"),
        start_number=0,
        text_style=TextStyle(bold=True),
    )


def test_parses_list_definition_levels_and_ignores_suggestions() -> None:
    assert ListDefinition.gdoc_parser.parse(
        {
            "listProperties": {
                "nestingLevels": [
                    {"glyphFormat": "%0", "glyphSymbol": "●"},
                    {
                        "glyphFormat": "%1.",
                        "glyphType": "DECIMAL",
                        "startNumber": 3,
                    },
                ]
            },
            "suggestedInsertionId": "ignored",
            "suggestedDeletionIds": ["ignored"],
            "suggestedListPropertiesChanges": {"ignored": {}},
        }
    ) == ListDefinition(
        levels=[
            ListLevel(glyph_format="%0", glyph_symbol="●"),
            ListLevel(glyph_format="%1.", glyph_type="DECIMAL", start_number=3),
        ]
    )
