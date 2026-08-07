import pytest

from gdocs_patch.models import (
    UNSET,
    Body,
    Dimension,
    Document,
    DocumentTab,
    SectionBreak,
    SectionColumn,
    SectionStyle,
    Tab,
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
