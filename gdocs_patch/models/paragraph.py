from typing import TYPE_CHECKING, ClassVar, Literal

from .base import UNSET, Color, Dimension, Model, UnsetType
from .document import StructuralElement

if TYPE_CHECKING:
    from gdocs_patch.parsers.base import GDocParser


class Link(Model):
    """Base for mutually exclusive text-link targets."""


class UrlLink(Link):
    gdoc_parser: ClassVar["GDocParser[UrlLink]"]

    def __init__(self, *, url: str) -> None:
        self.url = url


class TabLink(Link):
    gdoc_parser: ClassVar["GDocParser[TabLink]"]

    def __init__(self, *, tab_id: str) -> None:
        self.tab_id = tab_id


class BookmarkLink(Link):
    gdoc_parser: ClassVar["GDocParser[BookmarkLink]"]

    def __init__(
        self,
        *,
        bookmark_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.bookmark_id = bookmark_id
        self.tab_id = tab_id


class HeadingLink(Link):
    gdoc_parser: ClassVar["GDocParser[HeadingLink]"]

    def __init__(
        self,
        *,
        heading_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.heading_id = heading_id
        self.tab_id = tab_id


class TextStyle(Model):
    gdoc_parser: ClassVar["GDocParser[TextStyle]"]

    def __init__(
        self,
        *,
        bold: bool | UnsetType = UNSET,
        italic: bool | UnsetType = UNSET,
        underline: bool | UnsetType = UNSET,
        strikethrough: bool | UnsetType = UNSET,
        small_caps: bool | UnsetType = UNSET,
        baseline_offset: Literal[
            "BASELINE_OFFSET_UNSPECIFIED",
            "NONE",
            "SUPERSCRIPT",
            "SUBSCRIPT",
        ]
        | UnsetType = UNSET,
        font_size: Dimension | UnsetType = UNSET,
        font_family: str | UnsetType = UNSET,
        font_weight: int | UnsetType = UNSET,
        foreground_color: Color | None | UnsetType = UNSET,
        background_color: Color | None | UnsetType = UNSET,
        link: Link | UnsetType = UNSET,
    ) -> None:
        self.bold = bold
        self.italic = italic
        self.underline = underline
        self.strikethrough = strikethrough
        self.small_caps = small_caps
        self.baseline_offset = baseline_offset
        self.font_size = font_size
        self.font_family = font_family
        self.font_weight = font_weight
        self.foreground_color = foreground_color
        self.background_color = background_color
        self.link = link


class Bullet(Model):
    gdoc_parser: ClassVar["GDocParser[Bullet]"]

    def __init__(
        self,
        *,
        list_id: str,
        nesting_level: int = 0,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.list_id = list_id
        self.nesting_level = nesting_level
        self.text_style = text_style


class ParagraphBorder(Model):
    gdoc_parser: ClassVar["GDocParser[ParagraphBorder]"]

    def __init__(
        self,
        *,
        color: Color | None,
        width: Dimension,
        padding: Dimension,
        dash_style: Literal[
            "DASH_STYLE_UNSPECIFIED",
            "SOLID",
            "DOT",
            "DASH",
        ],
    ) -> None:
        self.color = color
        self.width = width
        self.padding = padding
        self.dash_style = dash_style


class TabStop(Model):
    gdoc_parser: ClassVar["GDocParser[TabStop]"]

    def __init__(
        self,
        *,
        offset: Dimension,
        alignment: Literal[
            "TAB_STOP_ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
        ],
    ) -> None:
        self.offset = offset
        self.alignment = alignment


class ParagraphStyle(Model):
    gdoc_parser: ClassVar["GDocParser[ParagraphStyle]"]

    def __init__(
        self,
        *,
        named_style_type: Literal[
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
        ]
        | UnsetType = UNSET,
        alignment: Literal[
            "ALIGNMENT_UNSPECIFIED",
            "START",
            "CENTER",
            "END",
            "JUSTIFIED",
        ]
        | UnsetType = UNSET,
        direction: Literal[
            "CONTENT_DIRECTION_UNSPECIFIED",
            "LEFT_TO_RIGHT",
            "RIGHT_TO_LEFT",
        ]
        | UnsetType = UNSET,
        line_spacing: float | UnsetType = UNSET,
        spacing_mode: Literal[
            "SPACING_MODE_UNSPECIFIED",
            "NEVER_COLLAPSE",
            "COLLAPSE_LISTS",
        ]
        | UnsetType = UNSET,
        space_above: Dimension | UnsetType = UNSET,
        space_below: Dimension | UnsetType = UNSET,
        indent_first_line: Dimension | UnsetType = UNSET,
        indent_start: Dimension | UnsetType = UNSET,
        indent_end: Dimension | UnsetType = UNSET,
        keep_lines_together: bool | UnsetType = UNSET,
        keep_with_next: bool | UnsetType = UNSET,
        avoid_widow_and_orphan: bool | UnsetType = UNSET,
        page_break_before: bool | UnsetType = UNSET,
        heading_id: str | UnsetType = UNSET,
        border_between: ParagraphBorder | UnsetType = UNSET,
        border_top: ParagraphBorder | UnsetType = UNSET,
        border_bottom: ParagraphBorder | UnsetType = UNSET,
        border_left: ParagraphBorder | UnsetType = UNSET,
        border_right: ParagraphBorder | UnsetType = UNSET,
        shading_color: Color | None | UnsetType = UNSET,
        tab_stops: list[TabStop] | UnsetType = UNSET,
    ) -> None:
        self.named_style_type = named_style_type
        self.alignment = alignment
        self.direction = direction
        self.line_spacing = line_spacing
        self.spacing_mode = spacing_mode
        self.space_above = space_above
        self.space_below = space_below
        self.indent_first_line = indent_first_line
        self.indent_start = indent_start
        self.indent_end = indent_end
        self.keep_lines_together = keep_lines_together
        self.keep_with_next = keep_with_next
        self.avoid_widow_and_orphan = avoid_widow_and_orphan
        self.page_break_before = page_break_before
        self.heading_id = heading_id
        self.border_between = border_between
        self.border_top = border_top
        self.border_bottom = border_bottom
        self.border_left = border_left
        self.border_right = border_right
        self.shading_color = shading_color
        self.tab_stops = tab_stops


class ParagraphElement(Model):
    pass


class TextRun(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[TextRun]"]

    def __init__(
        self,
        *,
        content: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.content = content
        self.text_style = text_style


class AutoText(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[AutoText]"]

    def __init__(
        self,
        *,
        auto_text_type: Literal[
            "TYPE_UNSPECIFIED",
            "PAGE_NUMBER",
            "PAGE_COUNT",
        ],
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.auto_text_type = auto_text_type
        self.text_style = text_style


class ColumnBreak(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[ColumnBreak]"]

    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.text_style = text_style


class DateElement(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[DateElement]"]

    def __init__(
        self,
        *,
        date_id: str,
        date_format: Literal[
            "DATE_FORMAT_UNSPECIFIED",
            "DATE_FORMAT_CUSTOM",
            "DATE_FORMAT_MONTH_DAY_ABBREVIATED",
            "DATE_FORMAT_MONTH_DAY_FULL",
            "DATE_FORMAT_MONTH_DAY_YEAR_ABBREVIATED",
            "DATE_FORMAT_ISO8601",
        ]
        | UnsetType = UNSET,
        display_text: str | UnsetType = UNSET,
        locale: str | UnsetType = UNSET,
        time_format: Literal[
            "TIME_FORMAT_UNSPECIFIED",
            "TIME_FORMAT_DISABLED",
            "TIME_FORMAT_HOUR_MINUTE",
            "TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
        ]
        | UnsetType = UNSET,
        time_zone_id: str | UnsetType = UNSET,
        timestamp: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.date_id = date_id
        self.date_format = date_format
        self.display_text = display_text
        self.locale = locale
        self.time_format = time_format
        self.time_zone_id = time_zone_id
        self.timestamp = timestamp
        self.text_style = text_style


class Equation(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[Equation]"]


class FootnoteReference(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[FootnoteReference]"]

    def __init__(
        self,
        *,
        footnote_id: str,
        footnote_number: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.footnote_id = footnote_id
        self.footnote_number = footnote_number
        self.text_style = text_style


class HorizontalRule(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[HorizontalRule]"]

    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.text_style = text_style


class InlineObjectReference(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[InlineObjectReference]"]

    def __init__(
        self,
        *,
        inline_object_id: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.inline_object_id = inline_object_id
        self.text_style = text_style


class PageBreak(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[PageBreak]"]

    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.text_style = text_style


class PersonReference(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[PersonReference]"]

    def __init__(
        self,
        *,
        person_id: str,
        email: str | UnsetType = UNSET,
        name: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.person_id = person_id
        self.email = email
        self.name = name
        self.text_style = text_style


class RichLink(ParagraphElement):
    gdoc_parser: ClassVar["GDocParser[RichLink]"]

    def __init__(
        self,
        *,
        rich_link_id: str,
        uri: str,
        title: str | UnsetType = UNSET,
        mime_type: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        self.rich_link_id = rich_link_id
        self.uri = uri
        self.title = title
        self.mime_type = mime_type
        self.text_style = text_style


class Paragraph(StructuralElement):
    gdoc_parser: ClassVar["GDocParser[Paragraph]"]

    def __init__(
        self,
        *,
        elements: list[ParagraphElement],
        style: ParagraphStyle | UnsetType = UNSET,
        bullet: Bullet | UnsetType = UNSET,
        positioned_object_ids: list[str] | UnsetType = UNSET,
    ) -> None:
        self.elements = elements
        self.style = style
        self.bullet = bullet
        self.positioned_object_ids = positioned_object_ids


class NamedStyle(Model):
    gdoc_parser: ClassVar["GDocParser[NamedStyle]"]

    def __init__(
        self,
        *,
        named_style_type: Literal[
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
        ],
        text_style: TextStyle | UnsetType = UNSET,
        paragraph_style: ParagraphStyle | UnsetType = UNSET,
    ) -> None:
        self.named_style_type = named_style_type
        self.text_style = text_style
        self.paragraph_style = paragraph_style
