from typing import Literal, cast

from .base import UNSET, Color, Dimension, IndexedNode, Model, UnsetType
from .document import StructuralElement


class Link(Model):
    """Base for mutually exclusive text-link targets."""


class UrlLink(Link):
    def __init__(self, *, url: str) -> None:
        self.url = url


class TabLink(Link):
    def __init__(self, *, tab_id: str) -> None:
        self.tab_id = tab_id


class BookmarkLink(Link):
    def __init__(
        self,
        *,
        bookmark_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.bookmark_id = bookmark_id
        self.tab_id = tab_id


class HeadingLink(Link):
    def __init__(
        self,
        *,
        heading_id: str,
        tab_id: str | UnsetType = UNSET,
    ) -> None:
        self.heading_id = heading_id
        self.tab_id = tab_id


class TextStyle(Model):
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


class ParagraphElement(IndexedNode):
    @property
    def utf16_width(self) -> int:
        return 1


class TextRun(ParagraphElement):
    def __init__(
        self,
        *,
        content: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.content = content
        self.text_style = text_style

    @property
    def utf16_width(self) -> int:
        return len(self.content.encode("utf-16-le", errors="surrogatepass")) // 2


class AutoText(ParagraphElement):
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
        super().__init__()
        self.auto_text_type = auto_text_type
        self.text_style = text_style


class ColumnBreak(ParagraphElement):
    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.text_style = text_style


class DateElement(ParagraphElement):
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
        super().__init__()
        self.date_id = date_id
        self.date_format = date_format
        self.display_text = display_text
        self.locale = locale
        self.time_format = time_format
        self.time_zone_id = time_zone_id
        self.timestamp = timestamp
        self.text_style = text_style


class Equation(ParagraphElement):
    pass


class FootnoteReference(ParagraphElement):
    def __init__(
        self,
        *,
        footnote_id: str,
        footnote_number: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.footnote_id = footnote_id
        self.footnote_number = footnote_number
        self.text_style = text_style


class HorizontalRule(ParagraphElement):
    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.text_style = text_style


class InlineObjectReference(ParagraphElement):
    def __init__(
        self,
        *,
        inline_object_id: str,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.inline_object_id = inline_object_id
        self.text_style = text_style


class PageBreak(ParagraphElement):
    def __init__(
        self,
        *,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.text_style = text_style


class PersonReference(ParagraphElement):
    def __init__(
        self,
        *,
        person_id: str,
        email: str | UnsetType = UNSET,
        name: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.person_id = person_id
        self.email = email
        self.name = name
        self.text_style = text_style


class RichLink(ParagraphElement):
    def __init__(
        self,
        *,
        rich_link_id: str,
        uri: str,
        title: str | UnsetType = UNSET,
        mime_type: str | UnsetType = UNSET,
        text_style: TextStyle | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        self.rich_link_id = rich_link_id
        self.uri = uri
        self.title = title
        self.mime_type = mime_type
        self.text_style = text_style


class Paragraph(StructuralElement):
    def __init__(
        self,
        *,
        elements: list[ParagraphElement],
        style: ParagraphStyle | UnsetType = UNSET,
        bullet: Bullet | UnsetType = UNSET,
        positioned_object_ids: list[str] | UnsetType = UNSET,
    ) -> None:
        super().__init__()
        for child in elements:
            self.add_child(child)
        self.style = style
        self.bullet = bullet
        self.positioned_object_ids = positioned_object_ids

    @property
    def elements(self) -> list[ParagraphElement]:
        return cast("list[ParagraphElement]", self.children)

    @property
    def children_start_index(self) -> int:
        return self.start_index

    @property
    def utf16_width(self) -> int:
        return sum(element.utf16_width for element in self.elements)


class NamedStyle(Model):
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
