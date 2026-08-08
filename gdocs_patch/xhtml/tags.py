from typing import Any, cast
from xml.etree import ElementTree

from .attributes import (
    BooleanAttribute,
    ChoiceAttribute,
    ColorAttribute,
    FloatAttribute,
    IntegerAttribute,
    LiteralAttribute,
    NonNegativeIntegerAttribute,
    PointAttribute,
    StringAttribute,
)
from .base import gdocs_name, xhtml_name
from .nodes import (
    UNSET,
    Child,
    Children,
    Decoder,
    Encoder,
    Field,
    Tag,
    Text,
    UnsetType,
    ValidationError,
)


class _BoundaryChildren(Field[list[ElementTree.Element]]):
    """Unmigrated child XML retained only at the generic boundary."""

    def get_default(self) -> list[ElementTree.Element]:
        return []

    def decode_from(
        self, element: ElementTree.Element, decoder: Decoder
    ) -> list[ElementTree.Element]:
        if element.text is not None and element.text.strip():
            decoder.fail("unexpected text")
        return list(element)

    def encode_into(
        self,
        value: list[ElementTree.Element] | UnsetType,
        element: ElementTree.Element,
        encoder: Encoder,
    ) -> None:
        del encoder
        element.extend(cast(list[ElementTree.Element], value))


def _text_style_attributes() -> tuple[
    BooleanAttribute,
    BooleanAttribute,
    BooleanAttribute,
    BooleanAttribute,
    BooleanAttribute,
    ChoiceAttribute,
    PointAttribute,
    StringAttribute,
    IntegerAttribute,
    ColorAttribute,
    ColorAttribute,
]:
    return (
        BooleanAttribute(gdocs_name("bold")),
        BooleanAttribute(gdocs_name("italic")),
        BooleanAttribute(gdocs_name("underline")),
        BooleanAttribute(gdocs_name("strikethrough")),
        BooleanAttribute(gdocs_name("small-caps")),
        ChoiceAttribute(
            gdocs_name("baseline-offset"),
            choices={
                "BASELINE_OFFSET_UNSPECIFIED",
                "NONE",
                "SUPERSCRIPT",
                "SUBSCRIPT",
            },
        ),
        PointAttribute(gdocs_name("font-size")),
        StringAttribute(gdocs_name("font-family")),
        IntegerAttribute(gdocs_name("font-weight")),
        ColorAttribute(
            transparent=LiteralAttribute(
                gdocs_name("foreground-color"), value="transparent"
            ),
            red=FloatAttribute(gdocs_name("foreground-red")),
            green=FloatAttribute(gdocs_name("foreground-green")),
            blue=FloatAttribute(gdocs_name("foreground-blue")),
        ),
        ColorAttribute(
            transparent=LiteralAttribute(
                gdocs_name("background-color"), value="transparent"
            ),
            red=FloatAttribute(gdocs_name("background-red")),
            green=FloatAttribute(gdocs_name("background-green")),
            blue=FloatAttribute(gdocs_name("background-blue")),
        ),
    )


class BreakTag(Tag):
    tag_name = xhtml_name("br")

    children = Children()


class SpanTag(Tag):
    tag_name = xhtml_name("span")

    (
        bold,
        italic,
        underline,
        strikethrough,
        small_caps,
        baseline_offset,
        font_size,
        font_family,
        font_weight,
        foreground_color,
        background_color,
    ) = _text_style_attributes()
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


class MetadataAnchorTag(Tag):
    tag_name = xhtml_name("a")
    field_order = ("href", "bookmark_id", "heading_id", "tab_id", "children")

    href = StringAttribute("href")
    tab_id = StringAttribute(gdocs_name("tab-id"))
    bookmark_id = StringAttribute(gdocs_name("bookmark-id"))
    heading_id = StringAttribute(gdocs_name("heading-id"))
    children = Children()

    def clean(self) -> None:
        primary = sum(
            value is not UNSET
            for value in (self.href, self.bookmark_id, self.heading_id)
        )
        if self.href is not UNSET:
            if primary == 1 and self.tab_id is UNSET:
                return
            raise ValidationError("invalid link target attribute combination")
        if self.bookmark_id is not UNSET and primary == 1:
            return
        if self.heading_id is not UNSET and primary == 1:
            return
        if self.tab_id is not UNSET and primary == 0:
            return
        raise ValidationError("invalid link target attribute combination")


class BackgroundColorTag(Tag):
    tag_name = gdocs_name("background-color")

    color = _structured_color_attribute()
    children = Children()


class DocumentStyleTag(Tag):
    tag_name = gdocs_name("document-style")

    document_mode = ChoiceAttribute(
        gdocs_name("document-mode"),
        choices={"DOCUMENT_MODE_UNSPECIFIED", "PAGES", "PAGELESS"},
    )
    page_width = PointAttribute(gdocs_name("page-width"))
    page_height = PointAttribute(gdocs_name("page-height"))
    margin_top = PointAttribute(gdocs_name("margin-top"))
    margin_bottom = PointAttribute(gdocs_name("margin-bottom"))
    margin_left = PointAttribute(gdocs_name("margin-left"))
    margin_right = PointAttribute(gdocs_name("margin-right"))
    margin_header = PointAttribute(gdocs_name("margin-header"))
    margin_footer = PointAttribute(gdocs_name("margin-footer"))
    default_header_id = StringAttribute(gdocs_name("default-header-id"))
    default_footer_id = StringAttribute(gdocs_name("default-footer-id"))
    even_page_header_id = StringAttribute(gdocs_name("even-page-header-id"))
    even_page_footer_id = StringAttribute(gdocs_name("even-page-footer-id"))
    first_page_header_id = StringAttribute(gdocs_name("first-page-header-id"))
    first_page_footer_id = StringAttribute(gdocs_name("first-page-footer-id"))
    use_even_page_header_footer = BooleanAttribute(
        gdocs_name("use-even-page-header-footer")
    )
    use_first_page_header_footer = BooleanAttribute(
        gdocs_name("use-first-page-header-footer")
    )
    use_custom_header_footer_margins = BooleanAttribute(
        gdocs_name("use-custom-header-footer-margins")
    )
    flip_page_orientation = BooleanAttribute(gdocs_name("flip-page-orientation"))
    page_number_start = IntegerAttribute(gdocs_name("page-number-start"))
    children = Children(Child(BackgroundColorTag, max_num=1))


class NamedStyleTag(Tag):
    tag_name = gdocs_name("named-style")

    named_style_type = ChoiceAttribute(
        gdocs_name("type"),
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
        required=True,
    )
    (
        bold,
        italic,
        underline,
        strikethrough,
        small_caps,
        baseline_offset,
        font_size,
        font_family,
        font_weight,
        foreground_color,
        background_color,
    ) = _text_style_attributes()
    children = Children(
        Child(MetadataAnchorTag, max_num=1),
        Child(NamedParagraphStyleTag, max_num=1),
    )


class NamedStylesTag(Tag):
    tag_name = gdocs_name("named-styles")

    children = Children(Child(NamedStyleTag))


class ListLevelTag(Tag):
    tag_name = gdocs_name("list-level")

    glyph_format = StringAttribute(gdocs_name("glyph-format"), required=True)
    glyph_type = ChoiceAttribute(
        gdocs_name("glyph-type"),
        choices={
            "GLYPH_TYPE_UNSPECIFIED",
            "NONE",
            "DECIMAL",
            "ZERO_DECIMAL",
            "UPPER_ALPHA",
            "ALPHA",
            "UPPER_ROMAN",
            "ROMAN",
        },
    )
    glyph_symbol = StringAttribute(gdocs_name("glyph-symbol"))
    alignment = ChoiceAttribute(
        gdocs_name("alignment"),
        choices={"BULLET_ALIGNMENT_UNSPECIFIED", "START", "CENTER", "END"},
        default="BULLET_ALIGNMENT_UNSPECIFIED",
    )
    indent_first_line = PointAttribute(gdocs_name("indent-first-line"))
    indent_start = PointAttribute(gdocs_name("indent-start"))
    start_number = IntegerAttribute(gdocs_name("start-number"), default=0)
    (
        bold,
        italic,
        underline,
        strikethrough,
        small_caps,
        baseline_offset,
        font_size,
        font_family,
        font_weight,
        foreground_color,
        background_color,
    ) = _text_style_attributes()
    children = Children(Child(MetadataAnchorTag, max_num=1))

    def clean(self) -> None:
        if (self.glyph_type is UNSET) == (self.glyph_symbol is UNSET):
            raise ValidationError(
                "exactly one of g:glyph-type and g:glyph-symbol is required"
            )


class ListDefinitionTag(Tag):
    tag_name = gdocs_name("list-definition")

    list_id = StringAttribute(gdocs_name("list-id"), required=True)
    children = Children(Child(ListLevelTag))


class ListDefinitionsTag(Tag):
    tag_name = gdocs_name("list-definitions")

    children = Children(Child(ListDefinitionTag))


class DocumentBodyTag(Tag):
    tag_name = gdocs_name("body")

    children = _BoundaryChildren()


class HeadersTag(Tag):
    tag_name = gdocs_name("headers")

    children = _BoundaryChildren()


class FootersTag(Tag):
    tag_name = gdocs_name("footers")

    children = _BoundaryChildren()


class FootnotesTag(Tag):
    tag_name = gdocs_name("footnotes")

    children = _BoundaryChildren()


class DocumentTabTag(Tag):
    tag_name = gdocs_name("document-tab")

    children = Children(
        Child(DocumentStyleTag, max_num=1),
        Child(NamedStylesTag, max_num=1),
        Child(ListDefinitionsTag, max_num=1),
        Child(DocumentBodyTag, max_num=1),
        Child(HeadersTag, max_num=1),
        Child(FootersTag, max_num=1),
        Child(FootnotesTag, max_num=1),
    )


class ChildTabsTag(Tag):
    tag_name = gdocs_name("child-tabs")

    children = Children(Child(lambda: TabTag))


class TabTag(Tag):
    tag_name = gdocs_name("tab")

    tab_id = StringAttribute(gdocs_name("tab-id"), required=True)
    title = StringAttribute(gdocs_name("title"), required=True)
    index = IntegerAttribute(gdocs_name("index"), required=True)
    nesting_level = NonNegativeIntegerAttribute(gdocs_name("nesting-level"), default=0)
    parent_tab_id = StringAttribute(gdocs_name("parent-tab-id"))
    icon_emoji = StringAttribute(gdocs_name("icon-emoji"))
    children = Children(
        Child(DocumentTabTag, max_num=1),
        Child(ChildTabsTag, max_num=1),
    )


class BodyTag(Tag):
    tag_name = xhtml_name("body")

    children = Children(Child(TabTag))


class HtmlTag(Tag):
    tag_name = xhtml_name("html")

    document_id = StringAttribute(gdocs_name("document-id"), required=True)
    title = StringAttribute(gdocs_name("title"), required=True)
    revision_id = StringAttribute(gdocs_name("revision-id"))
    suggestions_view_mode = ChoiceAttribute(
        gdocs_name("suggestions-view-mode"),
        choices={
            "DEFAULT_FOR_CURRENT_ACCESS",
            "SUGGESTIONS_INLINE",
            "PREVIEW_SUGGESTIONS_ACCEPTED",
            "PREVIEW_WITHOUT_SUGGESTIONS",
        },
    )
    children = Children(Child(BodyTag, min_num=1, max_num=1))


class ParagraphTag(Tag):
    tag_name = xhtml_name("p")

    children = Children(
        Child(ParagraphStyleTag, max_num=1),
        Child(SpanTag),
        text_error="unexpected text content",
        tail_error="unexpected text between paragraph elements",
    )
