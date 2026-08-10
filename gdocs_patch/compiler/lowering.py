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
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TabLink,
    TextStyle,
    UnsetType,
    UrlLink,
)

from .edit_script import (
    ApplyParagraphStyle,
    ApplyTableCellStyle,
    ApplyTableColumnProperties,
    ApplyTableRowStyle,
    ApplyTextStyle,
    CreateParagraphBullets,
    DeleteContent,
    DeleteParagraphBullets,
    DeleteTableColumn,
    DeleteTableRow,
    EditScript,
    InsertTable,
    InsertTableColumn,
    InsertTableRow,
    InsertText,
    MergeTableCells,
    UnmergeTableCells,
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
TABLE_COLUMN_FIELDS = "widthType,width"
TABLE_ROW_FIELDS = "minRowHeight,preventOverflow,tableHeader"
TABLE_CELL_STYLE_FIELDS = (
    "backgroundColor,borderLeft,borderRight,borderTop,borderBottom,paddingLeft,"
    "paddingRight,paddingTop,paddingBottom,contentAlignment"
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


def serialize_table_column(value: TableColumn | UnsetType) -> dict[str, object]:
    if isinstance(value, UnsetType):
        return {}

    result: dict[str, object] = {"widthType": value.width_type}
    if value.width is not UNSET:
        result["width"] = serialize_dimension(cast(Dimension, value.width))
    return result


def serialize_table_cell_border(value: TableCellBorder) -> dict[str, object]:
    return {
        "color": serialize_optional_color(value.color),
        "width": serialize_dimension(value.width),
        "dashStyle": value.dash_style,
    }


def serialize_table_cell_style(
    value: TableCellStyle | UnsetType,
) -> dict[str, object]:
    if isinstance(value, UnsetType):
        return {}

    result: dict[str, object] = {}
    if value.background_color is not UNSET:
        result["backgroundColor"] = serialize_optional_color(
            cast("Color | None", value.background_color)
        )
    if value.border_left is not UNSET:
        result["borderLeft"] = serialize_table_cell_border(
            cast(TableCellBorder, value.border_left)
        )
    if value.border_right is not UNSET:
        result["borderRight"] = serialize_table_cell_border(
            cast(TableCellBorder, value.border_right)
        )
    if value.border_top is not UNSET:
        result["borderTop"] = serialize_table_cell_border(
            cast(TableCellBorder, value.border_top)
        )
    if value.border_bottom is not UNSET:
        result["borderBottom"] = serialize_table_cell_border(
            cast(TableCellBorder, value.border_bottom)
        )
    if value.padding_left is not UNSET:
        result["paddingLeft"] = serialize_dimension(cast(Dimension, value.padding_left))
    if value.padding_right is not UNSET:
        result["paddingRight"] = serialize_dimension(
            cast(Dimension, value.padding_right)
        )
    if value.padding_top is not UNSET:
        result["paddingTop"] = serialize_dimension(cast(Dimension, value.padding_top))
    if value.padding_bottom is not UNSET:
        result["paddingBottom"] = serialize_dimension(
            cast(Dimension, value.padding_bottom)
        )
    if value.content_alignment is not UNSET:
        result["contentAlignment"] = value.content_alignment
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
    edit_index = 0
    while edit_index < len(edit_script.edits):
        edit = edit_script.edits[edit_index]
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
                bullet_edits = [edit]
                for following_edit in edit_script.edits[edit_index + 1 :]:
                    previous_edit = bullet_edits[-1]
                    if (
                        not isinstance(following_edit, CreateParagraphBullets)
                        or following_edit.start_index != previous_edit.end_index
                        or following_edit.bullet_preset.preset
                        != edit.bullet_preset.preset
                    ):
                        break
                    bullet_edits.append(following_edit)

                # Docs determines nesting from leading tabs, but only preserves
                # mixed levels when adjacent items are created in one request.
                # Insert from highest index to lowest so each insertion leaves
                # every remaining insertion location unchanged.
                for bullet_edit in reversed(bullet_edits):
                    nesting_level = bullet_edit.bullet_preset.nesting_level
                    if nesting_level > 0:
                        requests.append(
                            {
                                "insertText": {
                                    "location": {
                                        "index": bullet_edit.start_index,
                                        **context,
                                    },
                                    "text": "\t" * nesting_level,
                                }
                            }
                        )
                requests.append(
                    {
                        "createParagraphBullets": {
                            "range": {
                                "startIndex": bullet_edits[0].start_index,
                                "endIndex": bullet_edits[-1].end_index
                                + sum(
                                    bullet_edit.bullet_preset.nesting_level
                                    for bullet_edit in bullet_edits
                                ),
                                **context,
                            },
                            "bulletPreset": edit.bullet_preset.preset,
                        }
                    }
                )
                edit_index += len(bullet_edits)
                continue
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
            case InsertTable():
                # Docs inserts a newline before a new table, so its request
                # location is one code unit before the table's final index.
                requests.append(
                    {
                        "insertTable": {
                            "rows": edit.rows,
                            "columns": edit.columns,
                            "location": {"index": edit.index - 1, **context},
                        }
                    }
                )
            case InsertTableRow():
                requests.append(
                    {
                        "insertTableRow": {
                            "tableCellLocation": {
                                "tableStartLocation": {
                                    "index": edit.table_start_index,
                                    **context,
                                },
                                "rowIndex": edit.row_index,
                                "columnIndex": edit.column_index,
                            },
                            "insertBelow": edit.insert_below,
                        }
                    }
                )
            case InsertTableColumn():
                requests.append(
                    {
                        "insertTableColumn": {
                            "tableCellLocation": {
                                "tableStartLocation": {
                                    "index": edit.table_start_index,
                                    **context,
                                },
                                "rowIndex": edit.row_index,
                                "columnIndex": edit.column_index,
                            },
                            "insertRight": edit.insert_right,
                        }
                    }
                )
            case DeleteTableRow():
                requests.append(
                    {
                        "deleteTableRow": {
                            "tableCellLocation": {
                                "tableStartLocation": {
                                    "index": edit.table_start_index,
                                    **context,
                                },
                                "rowIndex": edit.row_index,
                                "columnIndex": edit.column_index,
                            }
                        }
                    }
                )
            case DeleteTableColumn():
                requests.append(
                    {
                        "deleteTableColumn": {
                            "tableCellLocation": {
                                "tableStartLocation": {
                                    "index": edit.table_start_index,
                                    **context,
                                },
                                "rowIndex": edit.row_index,
                                "columnIndex": edit.column_index,
                            }
                        }
                    }
                )
            case MergeTableCells():
                requests.append(
                    {
                        "mergeTableCells": {
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {
                                        "index": edit.table_start_index,
                                        **context,
                                    },
                                    "rowIndex": edit.row_index,
                                    "columnIndex": edit.column_index,
                                },
                                "rowSpan": edit.row_span,
                                "columnSpan": edit.column_span,
                            }
                        }
                    }
                )
            case UnmergeTableCells():
                requests.append(
                    {
                        "unmergeTableCells": {
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {
                                        "index": edit.table_start_index,
                                        **context,
                                    },
                                    "rowIndex": edit.row_index,
                                    "columnIndex": edit.column_index,
                                },
                                "rowSpan": edit.row_span,
                                "columnSpan": edit.column_span,
                            }
                        }
                    }
                )
            case ApplyTableColumnProperties():
                requests.append(
                    {
                        "updateTableColumnProperties": {
                            "tableStartLocation": {
                                "index": edit.table_start_index,
                                **context,
                            },
                            "columnIndices": [edit.column_index],
                            "tableColumnProperties": serialize_table_column(
                                edit.column_properties
                            ),
                            "fields": TABLE_COLUMN_FIELDS,
                        }
                    }
                )
            case ApplyTableRowStyle():
                table_row_style: dict[str, object] = {}
                if edit.min_height is not UNSET:
                    table_row_style["minRowHeight"] = serialize_dimension(
                        cast(Dimension, edit.min_height)
                    )
                if edit.prevent_overflow is not UNSET:
                    table_row_style["preventOverflow"] = edit.prevent_overflow
                if edit.is_header is not UNSET:
                    table_row_style["tableHeader"] = edit.is_header
                requests.append(
                    {
                        "updateTableRowStyle": {
                            "tableStartLocation": {
                                "index": edit.table_start_index,
                                **context,
                            },
                            "rowIndices": [edit.row_index],
                            "tableRowStyle": table_row_style,
                            "fields": TABLE_ROW_FIELDS,
                        }
                    }
                )
            case ApplyTableCellStyle():
                requests.append(
                    {
                        "updateTableCellStyle": {
                            "tableRange": {
                                "tableCellLocation": {
                                    "tableStartLocation": {
                                        "index": edit.table_start_index,
                                        **context,
                                    },
                                    "rowIndex": edit.row_index,
                                    "columnIndex": edit.column_index,
                                },
                                "rowSpan": edit.row_span,
                                "columnSpan": edit.column_span,
                            },
                            "tableCellStyle": serialize_table_cell_style(
                                edit.cell_style
                            ),
                            "fields": TABLE_CELL_STYLE_FIELDS,
                        }
                    }
                )
            case _:
                raise NotImplementedError(type(edit).__name__)
        edit_index += 1
    return requests
