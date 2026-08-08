from typing import Any, cast

from .attributes import (
    BooleanAttribute,
    ChoiceAttribute,
    ColorAttribute,
    FloatAttribute,
    IntegerAttribute,
    LiteralAttribute,
    NonNegativeIntegerAttribute,
    PointAttribute,
    PositiveIntegerAttribute,
    StringAttribute,
)
from .base import gdocs_name, xhtml_name
from .nodes import (
    UNSET,
    Child,
    Children,
    Field,
    Node,
    Tag,
    Text,
    UnsetType,
    ValidationError,
)


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

    owned_named_style_type = StringAttribute(gdocs_name("named-style-type"))
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
        fields.pop("owned_named_style_type")
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

    def validate_after_attributes(self) -> None:
        self._validate_target()

    def clean(self) -> None:
        self._validate_target()

    def _validate_target(self) -> None:
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
    field_order = (
        "document_mode",
        "default_header_id",
        "default_footer_id",
        "even_page_header_id",
        "even_page_footer_id",
        "first_page_header_id",
        "first_page_footer_id",
        "use_even_page_header_footer",
        "use_first_page_header_footer",
        "use_custom_header_footer_margins",
        "flip_page_orientation",
        "page_number_start",
        "page_width",
        "page_height",
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "margin_header",
        "margin_footer",
        "children",
    )

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


class BulletStyleTag(Tag):
    tag_name = gdocs_name("bullet-style")

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

    def validate_after_attributes(self) -> None:
        self._validate_glyph_identity()

    def clean(self) -> None:
        self._validate_glyph_identity()

    def _validate_glyph_identity(self) -> None:
        if (self.glyph_type is UNSET) == (self.glyph_symbol is UNSET):
            raise ValidationError(
                "exactly one of g:glyph-type and g:glyph-symbol is required"
            )


class ListDefinitionTag(Tag):
    tag_name = gdocs_name("list-definition")

    list_id = StringAttribute(gdocs_name("list-id"), required=True)
    children = Children(
        Child(ListLevelTag),
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
    )


class ListDefinitionsTag(Tag):
    tag_name = gdocs_name("list-definitions")

    children = Children(
        Child(ListDefinitionTag),
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
        unique_by=ListDefinitionTag.list_id,
        duplicate_error="duplicate list key {key!r}",
    )


class PositionedObjectTag(Tag):
    tag_name = gdocs_name("positioned-object")

    object_id = StringAttribute(gdocs_name("id"), required=True)
    children = Children()


class PositionedObjectsTag(Tag):
    tag_name = gdocs_name("positioned-objects")

    children = Children(Child(PositionedObjectTag))


class StyledParagraphElementTag(Tag):
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
    children = Children()


def _styled_paragraph_element_field_order(*identity_fields: str) -> tuple[str, ...]:
    return (
        *identity_fields,
        "bold",
        "italic",
        "underline",
        "strikethrough",
        "small_caps",
        "baseline_offset",
        "font_size",
        "font_family",
        "font_weight",
        "foreground_color",
        "background_color",
        "children",
    )


class AutoTextTag(StyledParagraphElementTag):
    tag_name = gdocs_name("auto-text")
    field_order = _styled_paragraph_element_field_order("auto_text_type")
    auto_text_type = ChoiceAttribute(
        gdocs_name("type"),
        choices={"TYPE_UNSPECIFIED", "PAGE_NUMBER", "PAGE_COUNT"},
        required=True,
    )


class ColumnBreakTag(StyledParagraphElementTag):
    tag_name = gdocs_name("column-break")
    field_order = _styled_paragraph_element_field_order()


class DateElementTag(StyledParagraphElementTag):
    tag_name = xhtml_name("time")
    field_order = _styled_paragraph_element_field_order(
        "date_id",
        "date_format",
        "time_format",
        "display_text",
        "locale",
        "time_zone_id",
        "timestamp",
    )
    date_id = StringAttribute(gdocs_name("date-id"), required=True)
    date_format = ChoiceAttribute(
        gdocs_name("date-format"),
        choices={
            "DATE_FORMAT_UNSPECIFIED",
            "DATE_FORMAT_CUSTOM",
            "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
            "DATE_FORMAT_MONTH_DAY_FULL",
            "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
            "DATE_FORMAT_ISO8601",
        },
    )
    display_text = StringAttribute(gdocs_name("display-text"))
    locale = StringAttribute(gdocs_name("locale"))
    time_format = ChoiceAttribute(
        gdocs_name("time-format"),
        choices={
            "TIME_FORMAT_UNSPECIFIED",
            "TIME_FORMAT_DISABLED",
            "TIME_FORMAT_HOUR_MINUTE",
            "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
        },
    )
    time_zone_id = StringAttribute(gdocs_name("time-zone-id"))
    timestamp = StringAttribute("datetime")


class EquationTag(Tag):
    tag_name = gdocs_name("equation")
    children = Children()


class FootnoteReferenceTag(StyledParagraphElementTag):
    tag_name = gdocs_name("footnote-reference")
    field_order = _styled_paragraph_element_field_order(
        "footnote_id", "footnote_number"
    )
    footnote_id = StringAttribute(gdocs_name("footnote-id"), required=True)
    footnote_number = StringAttribute(gdocs_name("footnote-number"), required=True)


class HorizontalRuleTag(StyledParagraphElementTag):
    tag_name = xhtml_name("hr")
    field_order = _styled_paragraph_element_field_order()


class InlineObjectReferenceTag(StyledParagraphElementTag):
    tag_name = gdocs_name("inline-object")
    field_order = _styled_paragraph_element_field_order("inline_object_id")
    inline_object_id = StringAttribute(gdocs_name("inline-object-id"), required=True)


class PageBreakTag(StyledParagraphElementTag):
    tag_name = gdocs_name("page-break")
    field_order = _styled_paragraph_element_field_order()


class PersonReferenceTag(StyledParagraphElementTag):
    tag_name = gdocs_name("person")
    field_order = _styled_paragraph_element_field_order("person_id", "email", "name")
    person_id = StringAttribute(gdocs_name("person-id"), required=True)
    email = StringAttribute(gdocs_name("email"))
    name = StringAttribute(gdocs_name("name"))


class RichLinkTag(StyledParagraphElementTag):
    tag_name = gdocs_name("rich-link")
    field_order = _styled_paragraph_element_field_order(
        "rich_link_id", "uri", "title", "mime_type"
    )
    rich_link_id = StringAttribute(gdocs_name("rich-link-id"), required=True)
    uri = StringAttribute(gdocs_name("uri"), required=True)
    title = StringAttribute(gdocs_name("title"))
    mime_type = StringAttribute(gdocs_name("mime-type"))


def _styled_paragraph_element_children() -> tuple[Child, ...]:
    return (
        Child(SpanTag),
        Child(AutoTextTag),
        Child(ColumnBreakTag),
        Child(DateElementTag),
        Child(FootnoteReferenceTag),
        Child(HorizontalRuleTag),
        Child(InlineObjectReferenceTag),
        Child(PageBreakTag),
        Child(PersonReferenceTag),
        Child(RichLinkTag),
    )


class _ContentAnchorChildren(Children):
    def validate(self, value: list[Node] | UnsetType) -> None:
        if not isinstance(value, list) or len(value) != 1:
            raise ValidationError(
                "link target must contain exactly one paragraph element"
            )
        super().validate(value)

    def validate_resolved_types(self, node_types: tuple[type[Node], ...]) -> None:
        if len(node_types) != 1:
            raise ValidationError(
                "link target must contain exactly one paragraph element"
            )
        super().validate_resolved_types(node_types)


class ContentAnchorTag(MetadataAnchorTag):
    children = _ContentAnchorChildren(
        *_styled_paragraph_element_children(), min_num=1, max_num=1
    )


class ParagraphVocabularyTag(Tag):
    children = Children(
        Child(ParagraphStyleTag, max_num=1),
        Child(PositionedObjectsTag, max_num=1),
        *_styled_paragraph_element_children(),
        Child(EquationTag),
        Child(ContentAnchorTag),
        positional_path_attributes={gdocs_name("auto-text"): gdocs_name("type")},
        text_error="unexpected text content",
        tail_error="unexpected text between paragraph elements",
    )


class GenericParagraphTag(ParagraphVocabularyTag):
    tag_name = gdocs_name("paragraph")


class UnspecifiedParagraphTag(ParagraphVocabularyTag):
    tag_name = gdocs_name("named-style-unspecified")


class ParagraphTag(ParagraphVocabularyTag):
    tag_name = xhtml_name("p")


class TitleTag(ParagraphVocabularyTag):
    tag_name = gdocs_name("title")


class SubtitleTag(ParagraphVocabularyTag):
    tag_name = gdocs_name("subtitle")


class Heading1Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h1")


class Heading2Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h2")


class Heading3Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h3")


class Heading4Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h4")


class Heading5Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h5")


class Heading6Tag(ParagraphVocabularyTag):
    tag_name = xhtml_name("h6")


_BULLET_PRESET_CHOICES = {
    "BULLET_GLYPH_PRESET_UNSPECIFIED",
    "BULLET_DISC_CIRCLE_SQUARE",
    "BULLET_DIAMONDX_ARROW3D_SQUARE",
    "BULLET_CHECKBOX",
    "BULLET_ARROW_DIAMOND_DISC",
    "BULLET_STAR_CIRCLE_SQUARE",
    "BULLET_ARROW3D_CIRCLE_SQUARE",
    "BULLET_LEFTTRIANGLE_DIAMOND_DISC",
    "BULLET_DIAMONDX_HOLLOWDIAMOND_SQUARE",
    "BULLET_DIAMOND_CIRCLE_SQUARE",
    "NUMBERED_DECIMAL_ALPHA_ROMAN",
    "NUMBERED_DECIMAL_ALPHA_ROMAN_PARENS",
    "NUMBERED_DECIMAL_NESTED",
    "NUMBERED_UPPERALPHA_ALPHA_ROMAN",
    "NUMBERED_UPPERROMAN_UPPERALPHA_DECIMAL",
    "NUMBERED_ZERODECIMAL_ALPHA_ROMAN",
}


class ListItemTag(Tag):
    tag_name = xhtml_name("li")

    nesting_level = IntegerAttribute(gdocs_name("nesting-level"), default=0)
    children = Children(
        Child(BulletStyleTag, max_num=1),
        Child(GenericParagraphTag),
        Child(UnspecifiedParagraphTag),
        Child(ParagraphTag),
        Child(TitleTag),
        Child(SubtitleTag),
        Child(Heading1Tag),
        Child(Heading2Tag),
        Child(Heading3Tag),
        Child(Heading4Tag),
        Child(Heading5Tag),
        Child(Heading6Tag),
        min_num=1,
        min_error="list item must contain exactly one paragraph",
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
    )

    def validate_resolved_child_types(
        self, child_types: tuple[type[Node], ...]
    ) -> None:
        paragraphs = sum(
            issubclass(child_type, ParagraphVocabularyTag) for child_type in child_types
        )
        if paragraphs != 1:
            raise ValidationError("list item must contain exactly one paragraph")

    def clean(self) -> None:
        if self.nesting_level is not UNSET and cast(int, self.nesting_level) < 0:
            raise ValidationError("nesting level must be non-negative")


class ListTag(Tag):
    tag_name = gdocs_name("list")

    list_id = StringAttribute(gdocs_name("list-id"))
    bullet_preset = ChoiceAttribute(
        gdocs_name("bullet-preset"), choices=_BULLET_PRESET_CHOICES
    )
    children = Children(
        Child(ListItemTag, min_num=1),
        min_num=1,
        min_error="list must contain at least one item",
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
    )

    def validate_after_child_shell(self) -> None:
        self._validate_identity()

    def clean(self) -> None:
        self._validate_identity()

    def _validate_identity(self) -> None:
        if (self.list_id is UNSET) == (self.bullet_preset is UNSET):
            raise ValidationError(
                "exactly one of g:list-id and g:bullet-preset is required"
            )


_TABLE_WIDTH_TYPES = {
    "WIDTH_TYPE_UNSPECIFIED",
    "EVENLY_DISTRIBUTED",
    "FIXED_WIDTH",
}
_TABLE_CONTENT_ALIGNMENTS = {
    "CONTENT_ALIGNMENT_UNSPECIFIED",
    "CONTENT_ALIGNMENT_UNSUPPORTED",
    "TOP",
    "MIDDLE",
    "BOTTOM",
}
_TABLE_DASH_STYLES = {"DASH_STYLE_UNSPECIFIED", "SOLID", "DOT", "DASH"}


class _CellSpanAttribute(PositiveIntegerAttribute):
    pass


class TableColumnTag(Tag):
    tag_name = xhtml_name("col")

    width_type = ChoiceAttribute(
        gdocs_name("width-type"), choices=_TABLE_WIDTH_TYPES, required=True
    )
    width = PointAttribute(gdocs_name("width"))
    children = Children()

    def clean(self) -> None:
        fixed = self.width_type == "FIXED_WIDTH"
        if fixed and self.width is UNSET:
            raise ValidationError("FIXED_WIDTH column requires width")
        if not fixed and self.width is not UNSET:
            raise ValidationError("width is forbidden unless width type is FIXED_WIDTH")


class TableColgroupTag(Tag):
    tag_name = xhtml_name("colgroup")
    children = Children(Child(TableColumnTag))


class TableCellBackgroundColorTag(Tag):
    tag_name = gdocs_name("background-color")
    color = _structured_color_attribute()
    children = Children()


class TableCellBorderTag(Tag):
    dash_style = ChoiceAttribute(
        gdocs_name("dash-style"), choices=_TABLE_DASH_STYLES, required=True
    )
    width = PointAttribute(gdocs_name("width"), required=True)
    children = Children(
        Child(
            ColorTag,
            min_num=1,
            max_num=1,
            min_error="missing required g:color child",
        )
    )


class TableCellBorderLeftTag(TableCellBorderTag):
    tag_name = gdocs_name("border-left")


class TableCellBorderRightTag(TableCellBorderTag):
    tag_name = gdocs_name("border-right")


class TableCellBorderTopTag(TableCellBorderTag):
    tag_name = gdocs_name("border-top")


class TableCellBorderBottomTag(TableCellBorderTag):
    tag_name = gdocs_name("border-bottom")


class TableCellStyleTag(Tag):
    tag_name = gdocs_name("cell-style")

    content_alignment = ChoiceAttribute(
        gdocs_name("content-alignment"), choices=_TABLE_CONTENT_ALIGNMENTS
    )
    padding_left = PointAttribute(gdocs_name("padding-left"))
    padding_right = PointAttribute(gdocs_name("padding-right"))
    padding_top = PointAttribute(gdocs_name("padding-top"))
    padding_bottom = PointAttribute(gdocs_name("padding-bottom"))
    children = Children(
        Child(TableCellBackgroundColorTag, max_num=1),
        Child(TableCellBorderLeftTag, max_num=1),
        Child(TableCellBorderRightTag, max_num=1),
        Child(TableCellBorderTopTag, max_num=1),
        Child(TableCellBorderBottomTag, max_num=1),
    )


def _table_cell_children() -> Children:
    return Children(
        Child(
            TableCellStyleTag,
            max_num=1,
            max_error="expected at most one g:cell-style child",
        ),
        Child(lambda: GenericParagraphTag),
        Child(lambda: UnspecifiedParagraphTag),
        Child(lambda: ParagraphTag),
        Child(lambda: TitleTag),
        Child(lambda: SubtitleTag),
        Child(lambda: Heading1Tag),
        Child(lambda: Heading2Tag),
        Child(lambda: Heading3Tag),
        Child(lambda: Heading4Tag),
        Child(lambda: Heading5Tag),
        Child(lambda: Heading6Tag),
        Child(lambda: ListTag),
        Child(lambda: TableTag),
        Child(lambda: TableOfContentsTag),
    )


class TableCellTag(Tag):
    tag_name = xhtml_name("td")

    cell_key = StringAttribute(gdocs_name("cell-key"))
    row_span = _CellSpanAttribute("rowspan")
    column_span = _CellSpanAttribute("colspan")
    children = _table_cell_children()

    def validate_after_descendants(self) -> None:
        self._validate_spans()

    def clean(self) -> None:
        self._validate_spans()

    def _validate_spans(self) -> None:
        for name, xml_name in (("row_span", "rowspan"), ("column_span", "colspan")):
            value = getattr(self, name)
            if value == 1:
                raise ValidationError(
                    "cell span must be greater than 1", attribute_name=xml_name
                )


class TableRowTag(Tag):
    tag_name = xhtml_name("tr")

    row_key = StringAttribute(gdocs_name("row-key"))
    min_height = PointAttribute(gdocs_name("min-height"))
    prevent_overflow = BooleanAttribute(gdocs_name("prevent-overflow"))
    is_header = BooleanAttribute(gdocs_name("is-header"))
    children = Children(Child(TableCellTag))


class TableBodyTag(Tag):
    tag_name = xhtml_name("tbody")
    children = Children(Child(TableRowTag))


class TableTag(Tag):
    tag_name = xhtml_name("table")

    table_key = StringAttribute(gdocs_name("table-key"))
    children = Children(
        Child(TableColgroupTag, max_num=1),
        Child(
            TableBodyTag,
            min_num=1,
            max_num=1,
            min_error="missing required tbody child",
        ),
    )


def _structural_children() -> Children:
    specs = [
        Child(lambda: GenericParagraphTag),
        Child(lambda: UnspecifiedParagraphTag),
        Child(lambda: ParagraphTag),
        Child(lambda: TitleTag),
        Child(lambda: SubtitleTag),
        Child(lambda: Heading1Tag),
        Child(lambda: Heading2Tag),
        Child(lambda: Heading3Tag),
        Child(lambda: Heading4Tag),
        Child(lambda: Heading5Tag),
        Child(lambda: Heading6Tag),
        Child(lambda: ListTag),
        Child(lambda: TableTag),
        Child(lambda: TableOfContentsTag),
    ]
    return Children(*specs)


class SectionColumnTag(Tag):
    tag_name = gdocs_name("column")

    width = PointAttribute(gdocs_name("width"), required=True)
    padding_end = PointAttribute(gdocs_name("padding-end"), required=True)
    children = Children()


class SectionColumnsTag(Tag):
    tag_name = gdocs_name("columns")

    children = Children(Child(SectionColumnTag))


class SectionStyleTag(Tag):
    tag_name = gdocs_name("section-style")

    column_separator_style = ChoiceAttribute(
        gdocs_name("column-separator-style"),
        choices={"COLUMN_SEPARATOR_STYLE_UNSPECIFIED", "NONE", "BETWEEN_EACH_COLUMN"},
    )
    content_direction = ChoiceAttribute(
        gdocs_name("content-direction"),
        choices={"CONTENT_DIRECTION_UNSPECIFIED", "LEFT_TO_RIGHT", "RIGHT_TO_LEFT"},
    )
    section_type = ChoiceAttribute(
        gdocs_name("section-type"),
        choices={"SECTION_TYPE_UNSPECIFIED", "CONTINUOUS", "NEXT_PAGE"},
    )
    default_header_id = StringAttribute(gdocs_name("default-header-id"))
    default_footer_id = StringAttribute(gdocs_name("default-footer-id"))
    even_page_header_id = StringAttribute(gdocs_name("even-page-header-id"))
    even_page_footer_id = StringAttribute(gdocs_name("even-page-footer-id"))
    first_page_header_id = StringAttribute(gdocs_name("first-page-header-id"))
    first_page_footer_id = StringAttribute(gdocs_name("first-page-footer-id"))
    use_first_page_header_footer = BooleanAttribute(
        gdocs_name("use-first-page-header-footer")
    )
    flip_page_orientation = BooleanAttribute(gdocs_name("flip-page-orientation"))
    page_number_start = IntegerAttribute(gdocs_name("page-number-start"))
    margin_top = PointAttribute(gdocs_name("margin-top"))
    margin_bottom = PointAttribute(gdocs_name("margin-bottom"))
    margin_left = PointAttribute(gdocs_name("margin-left"))
    margin_right = PointAttribute(gdocs_name("margin-right"))
    margin_header = PointAttribute(gdocs_name("margin-header"))
    margin_footer = PointAttribute(gdocs_name("margin-footer"))
    children = Children(Child(SectionColumnsTag, max_num=1))


class SectionTag(Tag):
    tag_name = xhtml_name("section")

    children = Children(
        Child(SectionStyleTag, min_num=1, max_num=1), *_structural_children().specs
    )


class DocumentBodyTag(Tag):
    tag_name = gdocs_name("body")

    children = Children(
        Child(lambda: SectionTag, min_num=1),
        min_num=1,
        min_error="body must contain at least one section",
        min_cardinality_before_text=True,
    )


class TableOfContentsTag(Tag):
    tag_name = gdocs_name("table-of-contents")

    children = Children(
        *_structural_children().specs,
        text_error="unexpected text content",
    )


class SegmentTag(Tag):
    key = StringAttribute(gdocs_name("key"), required=True)
    segment_id = StringAttribute(gdocs_name("segment-id"), required=True)
    children = Children(
        *_structural_children().specs,
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
    )


class HeaderTag(SegmentTag):
    tag_name = gdocs_name("header")


class FooterTag(SegmentTag):
    tag_name = gdocs_name("footer")


class FootnoteTag(SegmentTag):
    tag_name = gdocs_name("footnote")


def _segment_children(segment_type: type[SegmentTag]) -> Children:
    return Children(
        Child(segment_type),
        text_error="unexpected text content",
        tail_error="unexpected text after child element",
        unique_by=SegmentTag.key,
        duplicate_error="duplicate segment key {key!r}",
    )


class HeadersTag(Tag):
    tag_name = gdocs_name("headers")
    children = _segment_children(HeaderTag)


class FootersTag(Tag):
    tag_name = gdocs_name("footers")
    children = _segment_children(FooterTag)


class FootnotesTag(Tag):
    tag_name = gdocs_name("footnotes")
    children = _segment_children(FootnoteTag)


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
