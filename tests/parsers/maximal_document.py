from gdocs_patch.models import (
    AutoText,
    BookmarkLink,
    Bullet,
    Color,
    ColumnBreak,
    DateElement,
    Dimension,
    Document,
    DocumentStyle,
    DocumentTab,
    Equation,
    FootnoteReference,
    HeadingLink,
    HorizontalRule,
    InlineObjectReference,
    ListDefinition,
    ListLevel,
    NamedStyle,
    PageBreak,
    Paragraph,
    ParagraphBorder,
    ParagraphStyle,
    PersonReference,
    RichLink,
    SectionBreak,
    SectionColumn,
    SectionStyle,
    Segment,
    Tab,
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableOfContents,
    TableRow,
    TabLink,
    TabStop,
    TextRun,
    TextStyle,
    UrlLink,
)


def _dimension(magnitude: float) -> Dimension:
    return Dimension(magnitude=magnitude, unit="PT")


def _color(red: float, green: float = 0, blue: float = 0) -> Color:
    return Color(red=red, green=green, blue=blue)


def _paragraph_border(number: int) -> ParagraphBorder:
    return ParagraphBorder(
        color=_color(number / 10),
        width=_dimension(number),
        padding=_dimension(number + 0.5),
        dash_style="SOLID",
    )


def _cell_border(number: int) -> TableCellBorder:
    return TableCellBorder(
        color=_color(number / 10), width=_dimension(number), dash_style="DASH"
    )


def expected_maximal_document() -> Document:
    rich_paragraph = Paragraph(
        elements=[
            TextRun(
                content="Text",
                text_style=TextStyle(
                    bold=True,
                    italic=False,
                    underline=True,
                    strikethrough=False,
                    small_caps=True,
                    baseline_offset="SUPERSCRIPT",
                    font_size=_dimension(12),
                    font_family="Arial",
                    font_weight=700,
                    foreground_color=_color(0.1, 0.2, 0.3),
                    background_color=None,
                    link=UrlLink(url="https://example.test"),
                ),
            ),
            AutoText(
                auto_text_type="PAGE_NUMBER",
                text_style=TextStyle(link=TabLink(tab_id="tab-child")),
            ),
            ColumnBreak(
                text_style=TextStyle(
                    link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-root")
                )
            ),
            DateElement(
                date_id="date-1",
                date_format="DATE_FORMAT_ISO8601",
                display_text="2025-01-01",
                locale="en-US",
                time_format="TIME_FORMAT_HOUR_MINUTE_TIMEZONE",
                time_zone_id="UTC",
                timestamp="2025-01-01T12:00:00Z",
                text_style=TextStyle(
                    link=HeadingLink(heading_id="heading-1", tab_id="tab-root")
                ),
            ),
            Equation(),
            FootnoteReference(
                footnote_id="footnote-1",
                footnote_number="1",
                text_style=TextStyle(link=BookmarkLink(bookmark_id="bookmark-legacy")),
            ),
            HorizontalRule(
                text_style=TextStyle(link=HeadingLink(heading_id="heading-legacy"))
            ),
            InlineObjectReference(inline_object_id="inline-1", text_style=TextStyle()),
            PageBreak(text_style=TextStyle()),
            PersonReference(
                person_id="person-1",
                email="person@example.test",
                name="Person",
                text_style=TextStyle(),
            ),
            RichLink(
                rich_link_id="rich-1",
                uri="https://rich.test",
                title="Rich",
                mime_type="text/html",
                text_style=TextStyle(),
            ),
        ],
        style=ParagraphStyle(
            named_style_type="HEADING_1",
            alignment="JUSTIFIED",
            direction="LEFT_TO_RIGHT",
            line_spacing=115,
            spacing_mode="NEVER_COLLAPSE",
            space_above=_dimension(1),
            space_below=_dimension(2),
            indent_first_line=_dimension(3),
            indent_start=_dimension(4),
            indent_end=_dimension(5),
            keep_lines_together=True,
            keep_with_next=False,
            avoid_widow_and_orphan=True,
            page_break_before=False,
            heading_id="heading-1",
            border_between=_paragraph_border(1),
            border_top=_paragraph_border(2),
            border_bottom=_paragraph_border(3),
            border_left=_paragraph_border(4),
            border_right=_paragraph_border(5),
            shading_color=_color(0.5, 0.4, 0.3),
            tab_stops=[TabStop(offset=_dimension(36), alignment="CENTER")],
        ),
        bullet=Bullet(
            list_id="list-1", nesting_level=2, text_style=TextStyle(bold=True)
        ),
        positioned_object_ids=["positioned-1"],
    )
    section_break = SectionBreak(
        style=SectionStyle(
            columns=[
                SectionColumn(width=_dimension(200), padding_end=_dimension(10)),
                SectionColumn(width=_dimension(210), padding_end=_dimension(11)),
            ],
            column_separator_style="BETWEEN_EACH_COLUMN",
            content_direction="RIGHT_TO_LEFT",
            section_type="NEXT_PAGE",
            default_header_id="header-1",
            default_footer_id="footer-1",
            even_page_header_id="header-even",
            even_page_footer_id="footer-even",
            first_page_header_id="header-first",
            first_page_footer_id="footer-first",
            use_first_page_header_footer=True,
            flip_page_orientation=False,
            page_number_start=2,
            margin_top=_dimension(1),
            margin_bottom=_dimension(2),
            margin_left=_dimension(3),
            margin_right=_dimension(4),
            margin_header=_dimension(5),
            margin_footer=_dimension(6),
        )
    )
    nested_toc = TableOfContents(content=[Paragraph(elements=[])])
    table = Table(
        rows=[
            TableRow(
                cells=[
                    TableCell(
                        content=[
                            Paragraph(elements=[TextRun(content="Cell")]),
                            nested_toc,
                        ],
                        style=TableCellStyle(
                            row_span=2,
                            column_span=2,
                            background_color=None,
                            border_left=_cell_border(1),
                            border_right=_cell_border(2),
                            border_top=_cell_border(3),
                            border_bottom=_cell_border(4),
                            padding_left=_dimension(1),
                            padding_right=_dimension(2),
                            padding_top=_dimension(3),
                            padding_bottom=_dimension(4),
                            content_alignment="MIDDLE",
                        ),
                    ),
                    TableCell(content=[Paragraph(elements=[])], style=TableCellStyle()),
                ],
                min_height=_dimension(20),
                prevent_overflow=True,
                is_header=True,
            )
        ],
        column_styles=[
            TableColumn(width_type="FIXED_WIDTH", width=_dimension(100)),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
    )
    top_level_toc = TableOfContents(content=[Paragraph(elements=[])])
    document_style = DocumentStyle(
        background_color=_color(0.9, 0.8, 0.7),
        document_mode="PAGELESS",
        page_width=_dimension(612),
        page_height=_dimension(792),
        margin_top=_dimension(1),
        margin_bottom=_dimension(2),
        margin_left=_dimension(3),
        margin_right=_dimension(4),
        margin_header=_dimension(5),
        margin_footer=_dimension(6),
        default_header_id="header-1",
        default_footer_id="footer-1",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_even_page_header_footer=True,
        use_first_page_header_footer=False,
        use_custom_header_footer_margins=True,
        flip_page_orientation=False,
        page_number_start=7,
    )
    root_content = DocumentTab(
        body=[rich_paragraph, section_break, table, top_level_toc],
        headers={
            "header-1": Segment(segment_id="header-1", content=[Paragraph(elements=[])])
        },
        footers={"footer-1": Segment(segment_id="footer-1", content=[])},
        footnotes={
            "footnote-1": Segment(
                segment_id="footnote-1", content=[Paragraph(elements=[])]
            )
        },
        document_style=document_style,
        named_styles=[
            NamedStyle(
                named_style_type="NORMAL_TEXT",
                text_style=TextStyle(italic=True),
                paragraph_style=ParagraphStyle(alignment="START"),
            )
        ],
        lists={
            "list-1": ListDefinition(
                levels=[
                    ListLevel(
                        glyph_format="%0",
                        glyph_symbol="•",
                        alignment="START",
                        indent_first_line=_dimension(1),
                        indent_start=_dimension(2),
                        start_number=1,
                        text_style=TextStyle(bold=True),
                    ),
                    ListLevel(glyph_format="%1.", glyph_type="DECIMAL"),
                ]
            ),
            "list-defaults": ListDefinition(
                levels=[ListLevel(glyph_format="*", glyph_symbol="*")]
            ),
        },
    )
    child = Tab(
        tab_id="tab-child",
        title="Child",
        index=1,
        nesting_level=1,
        parent_tab_id="tab-root",
        icon_emoji="📝",
        children=[],
    )
    root = Tab(
        tab_id="tab-root",
        title="Root",
        index=0,
        nesting_level=0,
        icon_emoji="📄",
        content=root_content,
        children=[child],
    )
    empty = Tab(tab_id="tab-empty", title="No content", index=2, children=[])
    return Document(
        document_id="doc-max",
        title="Maximal",
        revision_id="revision-max",
        suggestions_view_mode="PREVIEW_WITHOUT_SUGGESTIONS",
        tabs=[root, empty],
    )
