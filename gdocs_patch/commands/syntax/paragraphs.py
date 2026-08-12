GUIDE = """\
Paragraphs contain text. In the simplest case, use `<p>` with one or more
`<span>` elements:

<p><span>Hello world</span></p>

Use `<h1>` through `<h6>` for headings. Title and subtitle paragraphs use
`<g:title>` and `<g:subtitle>`:

<h1><span>Project plan</span></h1>
<p><span>Start with a simple paragraph.</span></p>

Each span is one text run. Put text formatting directly on the span with `g`
attributes:

<p>
  <span>Normal text, then </span>
  <span g:bold="true" g:italic="true">bold italic text</span>
  <span g:font-size="14" g:foreground-red="0.8"
        g:foreground-green="0" g:foreground-blue="0"> and red text.</span>
</p>

Wrap a span in `<a>` to make a link:

<p>
  <span>Read the </span>
  <a href="https://example.com"><span>guide</span></a>
</p>

Paragraph formatting goes in a `<g:paragraph-style>` child. It comes before the
text in canonical output:

<p>
  <g:paragraph-style g:alignment="CENTER" g:space-below="8" />
  <span>Centered text with space below it.</span>
</p>

A paragraph's final newline is implicit, so do not add a `<br />` just to end
the paragraph. Use `<br />` only for an additional line break inside it.

For the complete list of paragraph and text-style attributes, run:
  gdocs-patch syntax paragraphs reference
"""

REFERENCE = """\
Paragraph syntax reference

Paragraph elements
------------------
Choose the element that matches the paragraph's named style:

  <p>                           NORMAL_TEXT
  <g:title>                     TITLE
  <g:subtitle>                  SUBTITLE
  <h1> through <h6>             HEADING_1 through HEADING_6

A paragraph can contain one optional `<g:paragraph-style>`, followed by text
runs and supported inline content. Its final newline is implicit. Inside a
span, `<br />` means an additional newline, `<g:vertical-tab />` means a vertical
tab, and `<g:form-feed />` means a form feed.

Text runs and text style
------------------------
Every text run is one `<span>`. These optional attributes are writable:

  g:bold                 true | false
  g:italic               true | false
  g:underline            true | false
  g:strikethrough        true | false
  g:small-caps           true | false
  g:baseline-offset      NONE | SUPERSCRIPT | SUBSCRIPT
  g:font-size            point value, for example 12
  g:font-family          string, for example Arial
  g:font-weight          integer

Foreground colors use all three `g:foreground-red`, `g:foreground-green`, and
`g:foreground-blue` attributes, with values from 0 to 1. Use
`g:foreground-color="transparent"` for transparent. Background colors use the
same forms with `background` in place of `foreground`.

Links wrap exactly one span:

  <a href="https://example.com"><span>URL</span></a>
  <a g:tab-id="TAB_ID"><span>Tab</span></a>
  <a g:bookmark-id="BOOKMARK_ID"><span>Bookmark</span></a>
  <a g:bookmark-id="BOOKMARK_ID" g:tab-id="TAB_ID"><span>Bookmark</span></a>
  <a g:heading-id="HEADING_ID"><span>Heading</span></a>
  <a g:heading-id="HEADING_ID" g:tab-id="TAB_ID"><span>Heading</span></a>

Paragraph style
---------------
Put these optional attributes on `<g:paragraph-style>`:

  g:alignment            START | CENTER | END | JUSTIFIED
  g:direction            LEFT_TO_RIGHT | RIGHT_TO_LEFT
  g:line-spacing         number
  g:spacing-mode         NEVER_COLLAPSE | COLLAPSE_LISTS
  g:space-above          point value
  g:space-below          point value
  g:indent-first-line    point value
  g:indent-start         point value
  g:indent-end           point value
  g:keep-lines-together  true | false
  g:keep-with-next       true | false
  g:avoid-widow-and-orphan
                         true | false
  g:page-break-before    true | false

Paragraph borders are `<g:border-between>`, `<g:border-top>`,
`<g:border-bottom>`, `<g:border-left>`, or `<g:border-right>` children. Each
requires `g:dash-style`, `g:width`, `g:padding`, and one `<g:color>`:

  <g:border-bottom g:dash-style="SOLID" g:width="1" g:padding="2">
    <g:color g:red="0" g:green="0" g:blue="0" />
  </g:border-bottom>

Dash styles are SOLID, DOT, and DASH. A color requires
all three RGB components from 0 to 1, or `g:transparent="true"`.

Shading is a `<g:shading-color>` child with the same RGB or transparent color
attributes. The XHTML codec also preserves heading IDs, tab stops, and
positioned-object IDs, but the compiler does not currently apply changes to
those fields.

Compiler limits
---------------
The compiler edits text, text styles, links, paragraph styles, and paragraph
boundaries. It can retain or delete an existing `<g:equation />`, but cannot
insert one. Other opaque inline elements may appear in XHTML returned by
`read`, but they are not yet editable compiler content.
"""
