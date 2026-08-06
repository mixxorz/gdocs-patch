from typing import cast

from gdocs_patch.models import (
    UNSET,
    BookmarkLink,
    Color,
    Dimension,
    HeadingLink,
    Link,
    ParagraphBorder,
    ParagraphStyle,
    TabLink,
    TextStyle,
    UnsetType,
    UrlLink,
)

from .edit_script import (
    ApplyParagraphStyle,
    ApplyTextStyle,
    CreateParagraphBullets,
    DeleteContent,
    DeleteParagraphBullets,
    EditScript,
    InsertText,
)

TEXT_STYLE_FIELDS = (
    "bold,italic,underline,strikethrough,smallCaps,baselineOffset,fontSize,"
    "weightedFontFamily,foregroundColor,backgroundColor,link"
)
PARAGRAPH_STYLE_FIELDS = (
    "namedStyleType,alignment,direction,lineSpacing,spacingMode,spaceAbove,"
    "spaceBelow,indentFirstLine,indentStart,indentEnd,keepLinesTogether,"
    "keepWithNext,avoidWidowAndOrphan,pageBreakBefore,borderBetween,borderTop,"
    "borderBottom,borderLeft,borderRight,shading"
)


def serialize_dimension(value: Dimension) -> dict[str, object]:
    return {"magnitude": value.magnitude, "unit": value.unit}


def serialize_optional_color(value: Color | None) -> dict[str, object]:
    if value is None:
        return {}
    return {
        "color": {
            "rgbColor": {
                "red": value.red,
                "green": value.green,
                "blue": value.blue,
            }
        }
    }


def serialize_link(value: Link) -> dict[str, object]:
    match value:
        case UrlLink():
            return {"url": value.url}
        case TabLink():
            return {"tabId": value.tab_id}
        case BookmarkLink():
            result: dict[str, object] = {"bookmarkId": value.bookmark_id}
            if value.tab_id is not UNSET:
                result["tabId"] = value.tab_id
            return result
        case HeadingLink():
            result = {"headingId": value.heading_id}
            if value.tab_id is not UNSET:
                result["tabId"] = value.tab_id
            return result
        case _:
            raise NotImplementedError(type(value).__name__)


def serialize_paragraph_border(value: ParagraphBorder) -> dict[str, object]:
    return {
        "color": serialize_optional_color(value.color),
        "width": serialize_dimension(value.width),
        "padding": serialize_dimension(value.padding),
        "dashStyle": value.dash_style,
    }


def serialize_text_style(value: TextStyle | UnsetType) -> dict[str, object]:
    if isinstance(value, UnsetType):
        return {}

    result: dict[str, object] = {}
    if value.bold is not UNSET:
        result["bold"] = value.bold
    if value.italic is not UNSET:
        result["italic"] = value.italic
    if value.underline is not UNSET:
        result["underline"] = value.underline
    if value.strikethrough is not UNSET:
        result["strikethrough"] = value.strikethrough
    if value.small_caps is not UNSET:
        result["smallCaps"] = value.small_caps
    if value.baseline_offset is not UNSET:
        result["baselineOffset"] = value.baseline_offset
    if value.font_size is not UNSET:
        result["fontSize"] = serialize_dimension(cast(Dimension, value.font_size))
    if value.font_family is not UNSET or value.font_weight is not UNSET:
        weighted_font_family: dict[str, object] = {}
        if value.font_family is not UNSET:
            weighted_font_family["fontFamily"] = value.font_family
        if value.font_weight is not UNSET:
            weighted_font_family["weight"] = value.font_weight
        result["weightedFontFamily"] = weighted_font_family
    if value.foreground_color is not UNSET:
        result["foregroundColor"] = serialize_optional_color(
            cast("Color | None", value.foreground_color)
        )
    if value.background_color is not UNSET:
        result["backgroundColor"] = serialize_optional_color(
            cast("Color | None", value.background_color)
        )
    if value.link is not UNSET:
        result["link"] = serialize_link(cast(Link, value.link))
    return result


def serialize_paragraph_style(
    value: ParagraphStyle | UnsetType,
) -> dict[str, object]:
    if isinstance(value, UnsetType):
        return {}

    result: dict[str, object] = {}
    if value.named_style_type is not UNSET:
        result["namedStyleType"] = value.named_style_type
    if value.alignment is not UNSET:
        result["alignment"] = value.alignment
    if value.direction is not UNSET:
        result["direction"] = value.direction
    if value.line_spacing is not UNSET:
        result["lineSpacing"] = value.line_spacing
    if value.spacing_mode is not UNSET:
        result["spacingMode"] = value.spacing_mode
    if value.space_above is not UNSET:
        result["spaceAbove"] = serialize_dimension(cast(Dimension, value.space_above))
    if value.space_below is not UNSET:
        result["spaceBelow"] = serialize_dimension(cast(Dimension, value.space_below))
    if value.indent_first_line is not UNSET:
        result["indentFirstLine"] = serialize_dimension(
            cast(Dimension, value.indent_first_line)
        )
    if value.indent_start is not UNSET:
        result["indentStart"] = serialize_dimension(cast(Dimension, value.indent_start))
    if value.indent_end is not UNSET:
        result["indentEnd"] = serialize_dimension(cast(Dimension, value.indent_end))
    if value.keep_lines_together is not UNSET:
        result["keepLinesTogether"] = value.keep_lines_together
    if value.keep_with_next is not UNSET:
        result["keepWithNext"] = value.keep_with_next
    if value.avoid_widow_and_orphan is not UNSET:
        result["avoidWidowAndOrphan"] = value.avoid_widow_and_orphan
    if value.page_break_before is not UNSET:
        result["pageBreakBefore"] = value.page_break_before
    if value.border_between is not UNSET:
        result["borderBetween"] = serialize_paragraph_border(
            cast(ParagraphBorder, value.border_between)
        )
    if value.border_top is not UNSET:
        result["borderTop"] = serialize_paragraph_border(
            cast(ParagraphBorder, value.border_top)
        )
    if value.border_bottom is not UNSET:
        result["borderBottom"] = serialize_paragraph_border(
            cast(ParagraphBorder, value.border_bottom)
        )
    if value.border_left is not UNSET:
        result["borderLeft"] = serialize_paragraph_border(
            cast(ParagraphBorder, value.border_left)
        )
    if value.border_right is not UNSET:
        result["borderRight"] = serialize_paragraph_border(
            cast(ParagraphBorder, value.border_right)
        )
    if value.shading_color is not UNSET:
        result["shading"] = {
            "backgroundColor": serialize_optional_color(
                cast("Color | None", value.shading_color)
            )
        }
    return result


def lower_edit_script(
    *,
    edit_script: EditScript,
    tab_id: str,
    segment_id: str | None = None,
) -> list[dict[str, object]]:
    context: dict[str, object] = {"tabId": tab_id}
    if segment_id is not None:
        context["segmentId"] = segment_id

    requests: list[dict[str, object]] = []
    for edit in edit_script.edits:
        match edit:
            case InsertText():
                requests.append(
                    {
                        "insertText": {
                            "location": {"index": edit.index, **context},
                            "text": edit.text,
                        }
                    }
                )
            case DeleteContent():
                requests.append(
                    {
                        "deleteContentRange": {
                            "range": {
                                "startIndex": edit.start_index,
                                "endIndex": edit.end_index,
                                **context,
                            }
                        }
                    }
                )
            case ApplyTextStyle():
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": {
                                "startIndex": edit.start_index,
                                "endIndex": edit.end_index,
                                **context,
                            },
                            "textStyle": serialize_text_style(edit.text_style),
                            "fields": TEXT_STYLE_FIELDS,
                        }
                    }
                )
            case ApplyParagraphStyle():
                requests.append(
                    {
                        "updateParagraphStyle": {
                            "range": {
                                "startIndex": edit.start_index,
                                "endIndex": edit.end_index,
                                **context,
                            },
                            "paragraphStyle": serialize_paragraph_style(
                                edit.paragraph_style
                            ),
                            "fields": PARAGRAPH_STYLE_FIELDS,
                        }
                    }
                )
            case CreateParagraphBullets():
                nesting_level = edit.bullet_preset.nesting_level
                if nesting_level > 0:
                    requests.append(
                        {
                            "insertText": {
                                "location": {"index": edit.start_index, **context},
                                "text": "\t" * nesting_level,
                            }
                        }
                    )
                requests.append(
                    {
                        "createParagraphBullets": {
                            "range": {
                                "startIndex": edit.start_index,
                                "endIndex": edit.end_index + nesting_level,
                                **context,
                            },
                            "bulletPreset": edit.bullet_preset.preset,
                        }
                    }
                )
            case DeleteParagraphBullets():
                requests.append(
                    {
                        "deleteParagraphBullets": {
                            "range": {
                                "startIndex": edit.start_index,
                                "endIndex": edit.end_index,
                                **context,
                            }
                        }
                    }
                )
            case _:
                raise NotImplementedError(type(edit).__name__)
    return requests
