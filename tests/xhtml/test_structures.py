import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Paragraph,
    SectionBreak,
    SectionColumn,
    SectionStyle,
    Tab,
    Table,
    TableCell,
    TableCellBorder,
    TableCellStyle,
    TableColumn,
    TableOfContents,
    TableRow,
    TextRun,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def document_with_section(style: SectionStyle) -> Document:
    return Document(
        document_id="doc-1",
        title="Sections",
        tabs=[
            Tab(
                tab_id="tab-1",
                title="Main",
                index=0,
                children=[],
                content=DocumentTab(body=Body(content=[SectionBreak(style=style)])),
            )
        ],
    )


def decoded_section_style(document: Document) -> SectionStyle:
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    section = content.body.content[0]
    assert isinstance(section, SectionBreak)
    return section.style


def test_round_trips_recursive_table_of_contents_in_body() -> None:
    table_of_contents = TableOfContents(
        content=[
            Paragraph(elements=[TextRun(content="First heading")]),
            Paragraph(elements=[TextRun(content="Second heading")]),
            TableOfContents(content=[]),
        ]
    )
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(table_of_contents)

    xhtml = serialize_document(document)

    assert xhtml.count("<g:table-of-contents") == 2
    assert "<g:table-of-contents />" in xhtml
    decoded_content = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded_content, DocumentTab)
    assert isinstance(decoded_content.body, Body)
    assert decoded_content.body.content[1] == table_of_contents


def test_rejects_body_section_inside_table_of_contents() -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(TableOfContents(content=[]))
    xhtml = serialize_document(document).replace(
        "<g:table-of-contents />",
        "<g:table-of-contents><section><g:section-style /></section></g:table-of-contents>",
    )

    with pytest.raises(
        XHTMLParseError, match="section elements are only valid in a body"
    ):
        deserialize_document(xhtml)


def test_round_trips_complete_section_style() -> None:
    style = SectionStyle(
        columns=[
            SectionColumn(
                width=Dimension(magnitude=234),
                padding_end=Dimension(magnitude=18),
            ),
            SectionColumn(
                width=Dimension(magnitude=240),
                padding_end=Dimension(magnitude=20),
            ),
        ],
        column_separator_style="BETWEEN_EACH_COLUMN",
        content_direction="LEFT_TO_RIGHT",
        section_type="NEXT_PAGE",
        default_header_id="header-default",
        default_footer_id="footer-default",
        even_page_header_id="header-even",
        even_page_footer_id="footer-even",
        first_page_header_id="header-first",
        first_page_footer_id="footer-first",
        use_first_page_header_footer=True,
        flip_page_orientation=False,
        page_number_start=3,
        margin_top=Dimension(magnitude=72),
        margin_bottom=Dimension(magnitude=73),
        margin_left=Dimension(magnitude=74),
        margin_right=Dimension(magnitude=75),
        margin_header=Dimension(magnitude=36),
        margin_footer=Dimension(magnitude=37),
    )

    xhtml = serialize_document(document_with_section(style))

    for fragment in (
        'g:column-separator-style="BETWEEN_EACH_COLUMN"',
        'g:content-direction="LEFT_TO_RIGHT"',
        'g:section-type="NEXT_PAGE"',
        'g:default-header-id="header-default"',
        'g:default-footer-id="footer-default"',
        'g:even-page-header-id="header-even"',
        'g:even-page-footer-id="footer-even"',
        'g:first-page-header-id="header-first"',
        'g:first-page-footer-id="footer-first"',
        'g:use-first-page-header-footer="true"',
        'g:flip-page-orientation="false"',
        'g:page-number-start="3"',
        'g:margin-top="72"',
        'g:margin-bottom="73"',
        'g:margin-left="74"',
        'g:margin-right="75"',
        'g:margin-header="36"',
        'g:margin-footer="37"',
        '<g:column g:width="234" g:padding-end="18" />',
        '<g:column g:width="240" g:padding-end="20" />',
    ):
        assert fragment in xhtml
    assert xhtml.index('g:width="234"') < xhtml.index('g:width="240"')

    decoded = decoded_section_style(deserialize_document(xhtml))
    assert decoded.column_separator_style == "BETWEEN_EACH_COLUMN"
    assert decoded.content_direction == "LEFT_TO_RIGHT"
    assert decoded.section_type == "NEXT_PAGE"
    assert decoded.default_header_id == "header-default"
    assert decoded.default_footer_id == "footer-default"
    assert decoded.even_page_header_id == "header-even"
    assert decoded.even_page_footer_id == "footer-even"
    assert decoded.first_page_header_id == "header-first"
    assert decoded.first_page_footer_id == "footer-first"
    assert decoded.use_first_page_header_footer is True
    assert decoded.flip_page_orientation is False
    assert decoded.page_number_start == 3
    assert isinstance(decoded.columns, list)
    assert decoded.columns == [
        SectionColumn(
            width=Dimension(magnitude=234, unit="PT"),
            padding_end=Dimension(magnitude=18, unit="PT"),
        ),
        SectionColumn(
            width=Dimension(magnitude=240, unit="PT"),
            padding_end=Dimension(magnitude=20, unit="PT"),
        ),
    ]
    for field in (
        "margin_top",
        "margin_bottom",
        "margin_left",
        "margin_right",
        "margin_header",
        "margin_footer",
    ):
        value = getattr(decoded, field)
        assert isinstance(value, Dimension)
        assert value.unit == "PT"


@pytest.mark.parametrize(("columns", "fragment"), [(UNSET, ""), ([], "<g:columns />")])
def test_preserves_unset_versus_empty_section_columns(
    columns: object, fragment: str
) -> None:
    style = SectionStyle(columns=columns)  # type: ignore[arg-type]

    xhtml = serialize_document(document_with_section(style))

    assert ("<g:columns" in xhtml) is bool(fragment)
    assert decoded_section_style(deserialize_document(xhtml)).columns == columns


@pytest.mark.parametrize("missing", ["g:width", "g:padding-end"])
def test_rejects_section_column_missing_required_dimension(missing: str) -> None:
    attributes = 'g:width="100" g:padding-end="10"'.replace(
        f'{missing}="{100 if missing == "g:width" else 10}"', ""
    )
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Bad">'
        '<body><g:tab g:tab-id="tab" g:title="Main" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style><g:columns>"
        f"<g:column {attributes} />"
        "</g:columns></g:section-style></section></g:body></g:document-tab>"
        "</g:tab></body></html>"
    )

    with pytest.raises(XHTMLParseError, match="missing required attribute"):
        deserialize_document(xhtml)


def document_with_table(table: Table) -> Document:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(table)
    return document


def test_round_trips_complete_recursive_table() -> None:
    border = TableCellBorder(
        color=Color(red=0.1, green=0.2, blue=0.3),
        width=Dimension(magnitude=1.5, unit="PT"),
        dash_style="SOLID",
    )
    styled_cell = TableCell(
        cell_key="merged-cell",
        style=TableCellStyle(
            row_span=2,
            column_span=2,
            background_color=Color(red=0.4, green=0.5, blue=0.6),
            border_left=border,
            border_right=border,
            border_top=border,
            border_bottom=border,
            padding_left=Dimension(magnitude=6, unit="PT"),
            padding_right=Dimension(magnitude=7, unit="PT"),
            padding_top=Dimension(magnitude=4, unit="PT"),
            padding_bottom=Dimension(magnitude=5, unit="PT"),
            content_alignment="MIDDLE",
        ),
        content=[
            Paragraph(elements=[TextRun(content="Cell paragraph")]),
            Table(rows=[TableRow(cells=[TableCell(content=[])])]),
            TableOfContents(content=[Paragraph(elements=[TextRun(content="TOC")])]),
        ],
    )
    table = Table(
        table_key="table-1",
        column_styles=[
            TableColumn(
                width_type="FIXED_WIDTH", width=Dimension(magnitude=144, unit="PT")
            ),
            TableColumn(width_type="EVENLY_DISTRIBUTED"),
        ],
        rows=[
            TableRow(
                row_key="header-row",
                min_height=Dimension(magnitude=24, unit="PT"),
                prevent_overflow=True,
                is_header=False,
                cells=[
                    styled_cell,
                    TableCell(
                        cell_key="transparent-cell",
                        style=TableCellStyle(background_color=None),
                        content=[],
                    ),
                ],
            ),
            TableRow(cells=[]),
        ],
    )

    xhtml = serialize_document(document_with_table(table))

    assert '<table g:table-key="table-1">' in xhtml
    assert '<col g:width-type="FIXED_WIDTH" g:width="144" />' in xhtml
    assert '<col g:width-type="EVENLY_DISTRIBUTED" />' in xhtml
    assert xhtml.index("<colgroup>") < xhtml.index("<tbody>")
    assert (
        '<tr g:row-key="header-row" g:min-height="24" '
        'g:prevent-overflow="true" g:is-header="false">'
    ) in xhtml
    assert '<td g:cell-key="merged-cell" rowspan="2" colspan="2">' in xhtml
    for fragment in (
        'g:content-alignment="MIDDLE"',
        'g:padding-left="6"',
        'g:padding-right="7"',
        'g:padding-top="4"',
        'g:padding-bottom="5"',
        '<g:background-color g:red="0.4" g:green="0.5" g:blue="0.6" />',
        '<g:border-left g:dash-style="SOLID" g:width="1.5">',
        '<g:border-right g:dash-style="SOLID" g:width="1.5">',
        '<g:border-top g:dash-style="SOLID" g:width="1.5">',
        '<g:border-bottom g:dash-style="SOLID" g:width="1.5">',
        '<g:color g:red="0.1" g:green="0.2" g:blue="0.3" />',
        '<g:background-color g:transparent="true" />',
        "<tr />",
    ):
        assert fragment in xhtml
    assert xhtml.count("<table") == 2
    assert deserialize_document(xhtml) == document_with_table(table)


@pytest.mark.parametrize(("columns", "fragment"), [(UNSET, ""), ([], "<colgroup />")])
def test_preserves_unset_versus_empty_table_columns(
    columns: object, fragment: str
) -> None:
    table = Table(rows=[], column_styles=columns)  # type: ignore[arg-type]

    xhtml = serialize_document(document_with_table(table))

    assert ("<colgroup" in xhtml) is bool(fragment)
    assert fragment in xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    decoded_table = decoded.body.content[1]
    assert isinstance(decoded_table, Table)
    assert decoded_table.column_styles == columns


def test_normalizes_default_only_table_cell_style_to_unset() -> None:
    table = Table(
        rows=[TableRow(cells=[TableCell(content=[], style=TableCellStyle())])]
    )

    decoded = deserialize_document(serialize_document(document_with_table(table)))

    content = decoded.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    decoded_table = content.body.content[1]
    assert isinstance(decoded_table, Table)
    assert decoded_table.rows[0].cells[0].style is UNSET


@pytest.mark.parametrize("attribute", ['rowspan="1"', 'colspan="1"'])
def test_rejects_explicit_default_cell_span(attribute: str) -> None:
    xhtml = serialize_document(
        document_with_table(Table(rows=[TableRow(cells=[TableCell(content=[])])]))
    ).replace("<td />", f"<td {attribute} />")

    with pytest.raises(XHTMLParseError, match="must be greater than 1"):
        deserialize_document(xhtml)


@pytest.mark.parametrize(
    ("column", "replacement"),
    [
        ('g:width-type="FIXED_WIDTH"', 'g:width-type="FIXED_WIDTH"'),
        (
            'g:width-type="EVENLY_DISTRIBUTED"',
            'g:width-type="EVENLY_DISTRIBUTED" g:width="10"',
        ),
    ],
)
def test_rejects_invalid_table_column_width(column: str, replacement: str) -> None:
    width = Dimension(magnitude=10) if "FIXED_WIDTH" in column else UNSET
    table = Table(
        rows=[],
        column_styles=[TableColumn(width_type=column.split('"')[1], width=width)],  # type: ignore[arg-type]
    )
    xhtml = serialize_document(document_with_table(table))
    if "FIXED_WIDTH" in column:
        xhtml = xhtml.replace(' g:width="10"', "")
    else:
        xhtml = xhtml.replace(column, replacement)

    with pytest.raises(XHTMLParseError, match="width"):
        deserialize_document(xhtml)


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        (
            '<g:background-color g:red="0.1" g:green="0.2" g:blue="0.3" />',
            '<g:background-color g:red="0.1" />',
            "requires red, green, and blue",
        ),
        (' g:width="1"', "", "missing required attribute"),
    ],
)
def test_rejects_invalid_table_cell_color_or_border(
    old: str, new: str, message: str
) -> None:
    border = TableCellBorder(
        color=Color(red=0, green=0, blue=0),
        width=Dimension(magnitude=1),
        dash_style="SOLID",
    )
    table = Table(
        rows=[
            TableRow(
                cells=[
                    TableCell(
                        content=[],
                        style=TableCellStyle(
                            background_color=Color(red=0.1, green=0.2, blue=0.3),
                            border_left=border,
                        ),
                    )
                ]
            )
        ]
    )
    xhtml = serialize_document(document_with_table(table)).replace(old, new, 1)

    with pytest.raises(XHTMLParseError, match=message):
        deserialize_document(xhtml)
