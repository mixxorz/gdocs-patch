from typing import Any

from .attributes import (
    BooleanAttribute,
    ChoiceAttribute,
    ColorAttribute,
    FloatAttribute,
    IntegerAttribute,
    LiteralAttribute,
    PointAttribute,
    StringAttribute,
)
from .base import gdocs_name, xhtml_name
from .nodes import Child, Children, Field, Tag, Text


class BreakTag(Tag):
    tag_name = xhtml_name("br")

    children = Children()


class SpanTag(Tag):
    tag_name = xhtml_name("span")

    bold = BooleanAttribute(gdocs_name("bold"))
    italic = BooleanAttribute(gdocs_name("italic"))
    underline = BooleanAttribute(gdocs_name("underline"))
    strikethrough = BooleanAttribute(gdocs_name("strikethrough"))
    small_caps = BooleanAttribute(gdocs_name("small-caps"))
    baseline_offset = ChoiceAttribute(
        gdocs_name("baseline-offset"),
        choices={
            "BASELINE_OFFSET_UNSPECIFIED",
            "NONE",
            "SUPERSCRIPT",
            "SUBSCRIPT",
        },
    )
    font_size = PointAttribute(gdocs_name("font-size"))
    font_family = StringAttribute(gdocs_name("font-family"))
    font_weight = IntegerAttribute(gdocs_name("font-weight"))
    foreground_color = ColorAttribute(
        transparent=LiteralAttribute(
            gdocs_name("foreground-color"), value="transparent"
        ),
        red=FloatAttribute(gdocs_name("foreground-red")),
        green=FloatAttribute(gdocs_name("foreground-green")),
        blue=FloatAttribute(gdocs_name("foreground-blue")),
    )
    background_color = ColorAttribute(
        transparent=LiteralAttribute(
            gdocs_name("background-color"), value="transparent"
        ),
        red=FloatAttribute(gdocs_name("background-red")),
        green=FloatAttribute(gdocs_name("background-green")),
        blue=FloatAttribute(gdocs_name("background-blue")),
    )
    children = Children(Child(Text), Child(BreakTag))


def _structured_color_attribute() -> ColorAttribute:
    return ColorAttribute(
        transparent=LiteralAttribute(gdocs_name("transparent"), value="true"),
        red=FloatAttribute(gdocs_name("red")),
        green=FloatAttribute(gdocs_name("green")),
        blue=FloatAttribute(gdocs_name("blue")),
        required=True,
    )


class ColorTag(Tag):
    tag_name = gdocs_name("color")

    color = _structured_color_attribute()
    children = Children()


class ShadingColorTag(Tag):
    tag_name = gdocs_name("shading-color")

    color = _structured_color_attribute()
    children = Children()


class ParagraphBorderTag(Tag):
    dash_style = ChoiceAttribute(
        gdocs_name("dash-style"),
        choices={"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"},
        required=True,
    )
    width = PointAttribute(gdocs_name("width"), required=True)
    padding = PointAttribute(gdocs_name("padding"), required=True)
    children = Children(Child(ColorTag, min_num=1, max_num=1))


class BorderBetweenTag(ParagraphBorderTag):
    tag_name = gdocs_name("border-between")


class BorderTopTag(ParagraphBorderTag):
    tag_name = gdocs_name("border-top")


class BorderBottomTag(ParagraphBorderTag):
    tag_name = gdocs_name("border-bottom")


class BorderLeftTag(ParagraphBorderTag):
    tag_name = gdocs_name("border-left")


class BorderRightTag(ParagraphBorderTag):
    tag_name = gdocs_name("border-right")


class TabStopTag(Tag):
    tag_name = gdocs_name("tab-stop")

    alignment = ChoiceAttribute(
        gdocs_name("alignment"),
        choices={
            "TAB_STOP_ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
        },
        required=True,
    )
    offset = PointAttribute(gdocs_name("offset"), required=True)
    children = Children()


class TabStopsTag(Tag):
    tag_name = gdocs_name("tab-stops")

    children = Children(Child(TabStopTag))


class ParagraphStyleTag(Tag):
    tag_name = gdocs_name("paragraph-style")

    alignment = ChoiceAttribute(
        gdocs_name("alignment"),
        choices={"ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END", "JUSTIFIED"},
    )
    direction = ChoiceAttribute(
        gdocs_name("direction"),
        choices={
            "CONTENT_DIRECTION_UNSPECIFIED",
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
        },
    )
    line_spacing = FloatAttribute(gdocs_name("line-spacing"))
    spacing_mode = ChoiceAttribute(
        gdocs_name("spacing-mode"),
        choices={
            "SPACING_MODE_UNSPECIFIED",
            "NEVER_COLLAPSE",
            "COLLAPSE_LISTS",
        },
    )
    space_above = PointAttribute(gdocs_name("space-above"))
    space_below = PointAttribute(gdocs_name("space-below"))
    indent_first_line = PointAttribute(gdocs_name("indent-first-line"))
    indent_start = PointAttribute(gdocs_name("indent-start"))
    indent_end = PointAttribute(gdocs_name("indent-end"))
    keep_lines_together = BooleanAttribute(gdocs_name("keep-lines-together"))
    keep_with_next = BooleanAttribute(gdocs_name("keep-with-next"))
    avoid_widow_and_orphan = BooleanAttribute(gdocs_name("avoid-widow-and-orphan"))
    page_break_before = BooleanAttribute(gdocs_name("page-break-before"))
    heading_id = StringAttribute(gdocs_name("heading-id"))
    children = Children(
        Child(BorderBetweenTag, max_num=1),
        Child(BorderTopTag, max_num=1),
        Child(BorderBottomTag, max_num=1),
        Child(BorderLeftTag, max_num=1),
        Child(BorderRightTag, max_num=1),
        Child(ShadingColorTag, max_num=1),
        Child(TabStopsTag, max_num=1),
    )


class NamedParagraphStyleTag(ParagraphStyleTag):
    named_style_type = ChoiceAttribute(
        gdocs_name("named-style-type"),
        choices={
            "NAMED_STYLE_TYPE_UNSPECIFIED",
            "NORMAL_TEXT",
            "TITLE",
            "SUBTITLE",
            "HEADING_1",
            "HEADING_2",
            "HEADING_3",
            "HEADING_4",
            "HEADING_5",
            "HEADING_6",
        },
    )

    @classmethod
    def fields(cls) -> dict[str, Field[Any]]:
        fields = super().fields()
        named_style_type = fields.pop("named_style_type")
        return {"named_style_type": named_style_type, **fields}


class ParagraphTag(Tag):
    tag_name = xhtml_name("p")

    children = Children(
        Child(ParagraphStyleTag, max_num=1),
        Child(SpanTag),
        text_error="unexpected text content",
        tail_error="unexpected text between paragraph elements",
    )
