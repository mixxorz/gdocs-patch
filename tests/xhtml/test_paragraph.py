import pytest

from gdocs_patch.models import (
    Body,
    BookmarkLink,
    Color,
    Dimension,
    Document,
    DocumentTab,
    Paragraph,
    ParagraphStyle,
    SectionBreak,
    SectionStyle,
    Tab,
    TextRun,
    TextStyle,
)
from gdocs_patch.xhtml import XHTMLParseError, deserialize_document, serialize_document


def document_with_runs(*runs: TextRun) -> Document:
    return Document(
        document_id="doc-1",
        title="Paragraph",
        tabs=[
            Tab(
                tab_id="tab-1",
                title="Main",
                index=0,
                children=[],
                content=DocumentTab(
                    body=Body(
                        content=[
                            SectionBreak(style=SectionStyle()),
                            Paragraph(
                                style=ParagraphStyle(named_style_type="NORMAL_TEXT"),
                                elements=list(runs),
                            ),
                        ]
                    )
                ),
            )
        ],
    )


def test_round_trips_text_style_link_colors_and_newlines() -> None:
    run = TextRun(
        content="First\nSecond\n",
        text_style=TextStyle(
            bold=True,
            italic=False,
            underline=True,
            strikethrough=False,
            small_caps=True,
            baseline_offset="SUPERSCRIPT",
            font_size=Dimension(magnitude=12, unit="UNIT_UNSPECIFIED"),
            font_family="Arial",
            font_weight=700,
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )

    xhtml = serialize_document(document_with_runs(run))

    assert '<a g:bookmark-id="bookmark-1" g:tab-id="tab-1">' in xhtml
    assert (
        '<span g:bold="true" g:italic="false" g:underline="true" '
        'g:strikethrough="false" g:small-caps="true" '
        'g:baseline-offset="SUPERSCRIPT" g:font-size="12" '
        'g:font-family="Arial" g:font-weight="700" '
        'g:foreground-red="0.1" g:foreground-green="0.2" '
        'g:foreground-blue="0.3" g:background-color="transparent">'
        "First<br />Second<br /></span>"
    ) in xhtml
    assert xhtml.count("<br />") == 2

    decoded = deserialize_document(xhtml)
    content = decoded.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)
    decoded_run = paragraph.elements[0]
    assert decoded_run == TextRun(
        content="First\nSecond\n",
        text_style=TextStyle(
            bold=True,
            italic=False,
            underline=True,
            strikethrough=False,
            small_caps=True,
            baseline_offset="SUPERSCRIPT",
            font_size=Dimension(magnitude=12, unit="PT"),
            font_family="Arial",
            font_weight=700,
            foreground_color=Color(red=0.1, green=0.2, blue=0.3),
            background_color=None,
            link=BookmarkLink(bookmark_id="bookmark-1", tab_id="tab-1"),
        ),
    )


def test_decodes_literal_line_feed_breaks_and_preserves_run_boundaries() -> None:
    xhtml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<html xmlns="http://www.w3.org/1999/xhtml" '
        'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Runs">'
        "<body>"
        '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
        "<g:document-tab><g:body><section><g:section-style />"
        "<p><span>Literal\nBreak<br />Tail</span><span /><span>Adjacent</span></p>"
        "</section></g:body></g:document-tab>"
        "</g:tab>"
        "</body></html>"
    )

    document = deserialize_document(xhtml)
    content = document.tabs[0].content
    assert isinstance(content, DocumentTab)
    assert isinstance(content.body, Body)
    paragraph = content.body.content[1]
    assert isinstance(paragraph, Paragraph)

    assert paragraph.elements == [
        TextRun(content="Literal\nBreak\nTail"),
        TextRun(content=""),
        TextRun(content="Adjacent"),
    ]


@pytest.mark.parametrize(
    "attributes",
    [
        'href="https://example.com" g:tab-id="tab-1"',
        'g:bookmark-id="bookmark-1" g:heading-id="heading-1"',
        "",
    ],
)
def test_rejects_invalid_link_target_combinations(attributes: str) -> None:
    with pytest.raises(XHTMLParseError, match="link target"):
        deserialize_document(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" '
            'xmlns:g="urn:gdocs-patch:xhtml:1" g:document-id="doc-1" g:title="Links">'
            "<body>"
            '<g:tab g:tab-id="tab-1" g:title="Main" g:index="0">'
            "<g:document-tab><g:body><section><g:section-style /><p>"
            f"<a {attributes}><span>Text</span></a>"
            "</p></section></g:body></g:document-tab>"
            "</g:tab>"
            "</body></html>"
        )
