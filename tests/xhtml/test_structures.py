import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    BookmarkLink,
    Bullet,
    BulletPreset,
    Color,
    Dimension,
    Document,
    DocumentTab,
    ListDefinition,
    ListLevel,
    Paragraph,
    SectionBreak,
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
    TextStyle,
    UrlLink,
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


def test_groups_adjacent_lists_by_kind_and_identity() -> None:
    paragraphs = [
        Paragraph(
            elements=[TextRun(content="existing zero\n")],
            bullet=Bullet(
                list_id="list-1",
                text_style=TextStyle(
                    bold=True, link=UrlLink(url="https://example.com/bullet")
                ),
            ),
        ),
        Paragraph(
            elements=[TextRun(content="existing two\n")],
            bullet=Bullet(
                list_id="list-1",
                nesting_level=2,
                text_style=TextStyle(italic=True),
            ),
        ),
        Paragraph(elements=[TextRun(content="break\n")]),
        Paragraph(
            elements=[TextRun(content="preset zero\n")],
            bullet=BulletPreset(preset="BULLET_DISC_CIRCLE_SQUARE"),
        ),
        Paragraph(
            elements=[TextRun(content="preset one\n")],
            bullet=BulletPreset(preset="BULLET_DISC_CIRCLE_SQUARE", nesting_level=1),
        ),
        Paragraph(
            elements=[TextRun(content="numbered\n")],
            bullet=BulletPreset(preset="NUMBERED_DECIMAL_ALPHA_ROMAN", nesting_level=1),
        ),
        Paragraph(
            elements=[TextRun(content="existing again\n")],
            bullet=Bullet(list_id="list-1"),
        ),
    ]
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    for paragraph in paragraphs:
        content.body.add_child(paragraph)

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Sections">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        '            <g:list g:list-id="list-1">\n'
        "              <li>\n"
        '                <g:bullet-style g:bold="true">\n'
        '                  <a href="https://example.com/bullet" />\n'
        "                </g:bullet-style>\n"
        "                <g:paragraph>\n"
        "                  <span>existing zero</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        '              <li g:nesting-level="2">\n'
        '                <g:bullet-style g:italic="true" />\n'
        "                <g:paragraph>\n"
        "                  <span>existing two</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        "            </g:list>\n"
        "            <g:paragraph>\n"
        "              <span>break</span>\n"
        "            </g:paragraph>\n"
        '            <g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">\n'
        "              <li>\n"
        "                <g:paragraph>\n"
        "                  <span>preset zero</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        '              <li g:nesting-level="1">\n'
        "                <g:paragraph>\n"
        "                  <span>preset one</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        "            </g:list>\n"
        '            <g:list g:bullet-preset="NUMBERED_DECIMAL_ALPHA_ROMAN">\n'
        '              <li g:nesting-level="1">\n'
        "                <g:paragraph>\n"
        "                  <span>numbered</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        "            </g:list>\n"
        '            <g:list g:list-id="list-1">\n'
        "              <li>\n"
        "                <g:paragraph>\n"
        "                  <span>existing again</span>\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        "            </g:list>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    assert decoded.body.content[1:] == paragraphs


def test_empty_existing_bullet_style_normalizes_to_unset() -> None:
    paragraph = Paragraph(
        elements=[TextRun(content="item")],
        bullet=Bullet(list_id="list-1", text_style=TextStyle()),
    )
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(paragraph)

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Sections">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        '            <g:list g:list-id="list-1">\n'
        "              <li>\n"
        "                <g:paragraph>\n"
        "                  <span>item</span>\n"
        "                  <span />\n"
        "                </g:paragraph>\n"
        "              </li>\n"
        "            </g:list>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert isinstance(decoded.body, Body)
    decoded_paragraph = decoded.body.content[1]
    assert isinstance(decoded_paragraph, Paragraph)
    assert isinstance(decoded_paragraph.bullet, Bullet)
    assert decoded_paragraph.bullet.text_style is UNSET


def test_list_definition_projection_preserves_order_and_levels() -> None:
    lists = {
        "empty": ListDefinition(levels=[]),
        "list-1": ListDefinition(
            levels=[
                ListLevel(
                    glyph_format="%0.",
                    glyph_type="DECIMAL",
                    alignment="START",
                    indent_first_line=Dimension(magnitude=18, unit="PT"),
                    indent_start=Dimension(magnitude=36, unit="PT"),
                    start_number=1,
                    text_style=TextStyle(
                        bold=True,
                        link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
                    ),
                ),
                ListLevel(glyph_format="%1", glyph_symbol="●"),
            ]
        ),
    }
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    content.lists = lists

    xhtml = serialize_document(document)

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Sections">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:list-definitions>\n"
        '          <g:list-definition g:list-id="empty" />\n'
        '          <g:list-definition g:list-id="list-1">\n'
        '            <g:list-level g:glyph-format="%0." '
        'g:glyph-type="DECIMAL" g:alignment="START" '
        'g:indent-first-line="18" g:indent-start="36" g:start-number="1" '
        'g:bold="true">\n'
        '              <a g:bookmark-id="bookmark-1" g:tab-id="tab-1" />\n'
        "            </g:list-level>\n"
        '            <g:list-level g:glyph-format="%1" g:glyph-symbol="●" />\n'
        "          </g:list-definition>\n"
        "        </g:list-definitions>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert list(decoded.lists) == ["empty", "list-1"]  # type: ignore[arg-type]
    assert decoded.lists == lists


@pytest.mark.parametrize(
    ("lists", "expected_xhtml"),
    [
        (
            UNSET,
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
            'g:title="Sections">\n'
            "  <body>\n"
            '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
            "      <g:document-tab>\n"
            "        <g:body>\n"
            "          <section>\n"
            "            <g:section-style />\n"
            "          </section>\n"
            "        </g:body>\n"
            "      </g:document-tab>\n"
            "    </g:tab>\n"
            "  </body>\n"
            "</html>\n",
        ),
        (
            {},
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
            'g:title="Sections">\n'
            "  <body>\n"
            '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
            "      <g:document-tab>\n"
            "        <g:list-definitions />\n"
            "        <g:body>\n"
            "          <section>\n"
            "            <g:section-style />\n"
            "          </section>\n"
            "        </g:body>\n"
            "      </g:document-tab>\n"
            "    </g:tab>\n"
            "  </body>\n"
            "</html>\n",
        ),
    ],
)
def test_wrapper_presence_distinguishes_unset_from_empty(
    lists: object, expected_xhtml: str
) -> None:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    content.lists = lists  # type: ignore[assignment]

    xhtml = serialize_document(document)

    assert xhtml == expected_xhtml
    decoded = deserialize_document(xhtml).tabs[0].content
    assert isinstance(decoded, DocumentTab)
    assert decoded.lists == lists


def xhtml_with_structure(structure: str, metadata: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc" g:title="Lists">'
        '<body><g:tab g:tab-id="tab" g:title="Main" g:index="0">'
        f"<g:document-tab>{metadata}<g:body><section><g:section-style />"
        f"{structure}"
        "</section></g:body></g:document-tab></g:tab></body></html>"
    )


@pytest.mark.parametrize(
    "structure",
    [
        "<g:list><li><p /></li></g:list>",
        (
            '<g:list g:list-id="id" g:bullet-preset="BULLET_CHECKBOX">'
            "<li><p /></li></g:list>"
        ),
    ],
)
def test_list_requires_exactly_one_identity(structure: str) -> None:
    with pytest.raises(XHTMLParseError, match="exactly one"):
        deserialize_document(xhtml_with_structure(structure))


def test_list_item_requires_exactly_one_paragraph() -> None:
    structure = '<g:list g:list-id="id"><li><p /><p /></li></g:list>'

    with pytest.raises(XHTMLParseError, match="exactly one paragraph"):
        deserialize_document(xhtml_with_structure(structure))


def test_list_item_nesting_level_must_be_non_negative() -> None:
    structure = '<g:list g:list-id="id"><li g:nesting-level="-1"><p /></li></g:list>'

    with pytest.raises(XHTMLParseError) as error:
        deserialize_document(xhtml_with_structure(structure))

    assert "/li[1] " in str(error.value)
    assert str(error.value).endswith(": nesting level must be non-negative")
    assert "/@g:nesting-level" not in str(error.value)


@pytest.mark.parametrize(
    "level",
    [
        '<g:list-level g:glyph-format="%0" />',
        (
            '<g:list-level g:glyph-format="%0" g:glyph-type="DECIMAL" '
            'g:glyph-symbol="x" />'
        ),
    ],
)
def test_list_level_requires_exactly_one_glyph_source(level: str) -> None:
    metadata = (
        '<g:list-definitions><g:list-definition g:list-id="id">'
        f"{level}</g:list-definition></g:list-definitions>"
    )

    with pytest.raises(XHTMLParseError, match="exactly one"):
        deserialize_document(xhtml_with_structure("", metadata))


def document_with_table(table: Table) -> Document:
    document = document_with_section(SectionStyle())
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    content.body.add_child(table)
    return document


def test_table_projection_supports_recursion_and_semantic_defaults() -> None:
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
            padding_left=Dimension(magnitude=6, unit="PT"),
            content_alignment="MIDDLE",
        ),
        content=[
            Paragraph(elements=[TextRun(content="Cell paragraph\n")]),
            Table(rows=[TableRow(cells=[TableCell(content=[])])]),
            TableOfContents(content=[Paragraph(elements=[TextRun(content="TOC\n")])]),
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
                is_header=True,
                cells=[
                    styled_cell,
                    TableCell(
                        cell_key="transparent-cell",
                        style=TableCellStyle(background_color=None),
                        content=[],
                    ),
                ],
            ),
            TableRow(cells=[], is_header=False),
        ],
    )

    xhtml = serialize_document(document_with_table(table))

    assert xhtml == (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" '
        'g:title="Sections">\n'
        "  <body>\n"
        '    <g:tab g:tab-id="tab-1" g:title="Main" g:index="0">\n'
        "      <g:document-tab>\n"
        "        <g:body>\n"
        "          <section>\n"
        "            <g:section-style />\n"
        '            <table g:table-key="table-1">\n'
        "              <colgroup>\n"
        '                <col g:width-type="FIXED_WIDTH" g:width="144" />\n'
        '                <col g:width-type="EVENLY_DISTRIBUTED" />\n'
        "              </colgroup>\n"
        "              <tbody>\n"
        '                <tr g:row-key="header-row" g:min-height="24" '
        'g:prevent-overflow="true" g:is-header="true">\n'
        '                  <td g:cell-key="merged-cell" rowspan="2" colspan="2">\n'
        '                    <g:cell-style g:content-alignment="MIDDLE" '
        'g:padding-left="6">\n'
        '                      <g:background-color g:red="0.4" g:green="0.5" '
        'g:blue="0.6" />\n'
        '                      <g:border-left g:dash-style="SOLID" '
        'g:width="1.5">\n'
        '                        <g:color g:red="0.1" g:green="0.2" '
        'g:blue="0.3" />\n'
        "                      </g:border-left>\n"
        "                    </g:cell-style>\n"
        "                    <g:paragraph>\n"
        "                      <span>Cell paragraph</span>\n"
        "                    </g:paragraph>\n"
        "                    <table>\n"
        "                      <tbody>\n"
        "                        <tr>\n"
        "                          <td />\n"
        "                        </tr>\n"
        "                      </tbody>\n"
        "                    </table>\n"
        "                    <g:table-of-contents>\n"
        "                      <g:paragraph>\n"
        "                        <span>TOC</span>\n"
        "                      </g:paragraph>\n"
        "                    </g:table-of-contents>\n"
        "                  </td>\n"
        '                  <td g:cell-key="transparent-cell">\n'
        "                    <g:cell-style>\n"
        '                      <g:background-color g:transparent="true" />\n'
        "                    </g:cell-style>\n"
        "                  </td>\n"
        "                </tr>\n"
        '                <tr g:is-header="false" />\n'
        "              </tbody>\n"
        "            </table>\n"
        "          </section>\n"
        "        </g:body>\n"
        "      </g:document-tab>\n"
        "    </g:tab>\n"
        "  </body>\n"
        "</html>\n"
    )
    expected_document = document_with_table(table)
    decoded_document = deserialize_document(xhtml)
    assert decoded_document == expected_document


def test_default_only_table_cell_style_normalizes_to_unset() -> None:
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
def test_explicit_default_cell_spans_are_rejected(attribute: str) -> None:
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
def test_table_column_width_matches_width_type(column: str, replacement: str) -> None:
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


def test_structured_table_cell_color_requires_complete_rgb() -> None:
    table = Table(
        rows=[
            TableRow(
                cells=[
                    TableCell(
                        content=[],
                        style=TableCellStyle(
                            background_color=Color(red=0.1, green=0.2, blue=0.3)
                        ),
                    )
                ]
            )
        ]
    )
    xhtml = serialize_document(document_with_table(table)).replace(
        '<g:background-color g:red="0.1" g:green="0.2" g:blue="0.3" />',
        '<g:background-color g:red="0.1" />',
    )

    with pytest.raises(XHTMLParseError, match="requires red, green, and blue"):
        deserialize_document(xhtml)
