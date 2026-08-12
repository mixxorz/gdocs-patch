XHTML_SYNTAX_OVERVIEW = """\
gdocs-patch represents a complete Google document as canonical XHTML.

Standard XHTML elements describe familiar document content such as paragraphs,
headings, links, lists, tables, and sections. Elements and attributes in the
`g` namespace preserve Google Docs-specific structure and metadata, including
tabs, styles, document IDs, and section settings.

Use `gdocs-patch read` to get this representation. Edit the returned XHTML
without removing its surrounding document structure, then use `write` to apply
the complete result or `edit` to make exact replacements. The XML declaration
and the XHTML and gdocs-patch namespace declarations are required.

A document can also contain existing headers, footers, and footnotes. You can
edit supported content inside them, but you cannot create or remove those
regions yet.

Basic example:

<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:g="urn:gdocs-patch:xhtml:1"
      g:document-id="DOCUMENT_ID"
      g:title="Example">
  <body>
    <g:tab g:tab-id="TAB_ID" g:title="Main" g:index="0">
      <g:document-tab>
        <g:body>
          <section>
            <g:section-style />
            <h1><span>Hello</span></h1>
            <p><span>This is a paragraph.</span></p>
          </section>
        </g:body>
      </g:document-tab>
    </g:tab>
  </body>
</html>

For more detail, use one of these commands:
  gdocs-patch syntax paragraphs
  gdocs-patch syntax lists
  gdocs-patch syntax tables
  gdocs-patch syntax equations
  gdocs-patch syntax sections
"""

PARAGRAPHS_SYNTAX = """\
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
"""

LISTS_SYNTAX = """\
A list is a group of paragraphs. Each `<li>` contains one paragraph:

<g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">
  <li><p><span>First item</span></p></li>
  <li><p><span>Second item</span></p></li>
</g:list>

Use `g:nesting-level` when an item is nested. Level 0 is the default:

<g:list g:bullet-preset="BULLET_DISC_CIRCLE_SQUARE">
  <li><p><span>Parent item</span></p></li>
  <li g:nesting-level="1"><p><span>Nested item</span></p></li>
</g:list>

When `read` returns an existing list, it uses `g:list-id`. Keep that ID when you
want to preserve and edit the same Google list:

<g:list g:list-id="existing-list-id">
  <li><p><span>Existing item</span></p></li>
  <li><p><span>Another item</span></p></li>
</g:list>

Use `g:bullet-preset` for a new list and `g:list-id` for an existing one, never
both. Google Docs cannot recreate arbitrary custom bullet glyphs through its
batch-update API, so new lists must use a supported preset. The CLI currently
does not opt into normalizing a customized existing list to a preset.
"""

TABLES_SYNTAX = """\
Tables use the normal XHTML table shape. Put rows inside one `<tbody>`, and put
paragraphs or other supported document content inside each cell:

<table>
  <tbody>
    <tr>
      <td><p><span>Top left</span></p></td>
      <td><p><span>Top right</span></p></td>
    </tr>
    <tr>
      <td><p><span>Bottom left</span></p></td>
      <td><p><span>Bottom right</span></p></td>
    </tr>
  </tbody>
</table>

Tables returned by `read` can carry opaque keys. Keep these keys when a target
table, row, or cell represents the same existing object:

<table g:table-key="table-key">
  <tbody>
    <tr g:row-key="row-key">
      <td g:cell-key="cell-key"><p><span>Updated text</span></p></td>
    </tr>
  </tbody>
</table>

Omit a key when you are adding a new table, row, or cell. The compiler uses the
keys to distinguish retained structures from new ones; they do not need to be
meaningful or globally unique.

Use standard `rowspan` and `colspan` attributes for merged cells. Column, row,
and cell formatting is also supported through `<colgroup>`, row attributes,
and `<g:cell-style>` metadata:

<table>
  <colgroup>
    <col g:width-type="FIXED_WIDTH" g:width="144" />
    <col g:width-type="EVENLY_DISTRIBUTED" />
  </colgroup>
  <tbody>
    <tr g:min-height="24">
      <td colspan="2">
        <g:cell-style g:content-alignment="MIDDLE" />
        <p><span>Merged cell</span></p>
      </td>
    </tr>
  </tbody>
</table>
"""

EQUATIONS_SYNTAX = """\
An equation is represented by one opaque marker inside a paragraph:

<p>
  <span>The result is </span>
  <g:equation />
  <span>.</span>
</p>

Google's document response does not expose the equation expression, so the XHTML
cannot show or edit its formula. Keeping the marker in the target preserves an
existing equation, and removing it deletes the equation.

The Google Docs batch-update API cannot insert an equation. Adding a new
`<g:equation />` where the source document did not already have one will make
compilation fail rather than silently produce the wrong document.
"""

SECTIONS_SYNTAX = """\
Every document body starts with a section. A section contains its settings and
then its paragraphs, tables, and other body content:

<g:body>
  <section>
    <g:section-style />
    <p><span>First section</span></p>
  </section>
</g:body>

Add another `<section>` when the document needs another section break. Give a
new break an explicit `g:section-type`:

<g:body>
  <section>
    <g:section-style />
    <p><span>First section</span></p>
  </section>
  <section>
    <g:section-style g:section-type="NEXT_PAGE" />
    <p><span>Starts on the next page</span></p>
  </section>
</g:body>

Section settings live on `<g:section-style>`. For example, margins are point
values, and columns use nested metadata:

<g:section-style g:section-type="CONTINUOUS"
                 g:margin-left="72" g:margin-right="72">
  <g:columns>
    <g:column g:width="234" g:padding-end="18" />
    <g:column g:width="234" g:padding-end="18" />
  </g:columns>
</g:section-style>

Sections exist only in a document body, not inside headers, footers, footnotes,
or table cells. A retained section break cannot change its section type, and a
concrete section setting cannot currently be cleared back to an unspecified
value. Other supported section-style changes are compiled normally.
"""

SYNTAX_TOPICS = {
    "paragraphs": PARAGRAPHS_SYNTAX,
    "lists": LISTS_SYNTAX,
    "tables": TABLES_SYNTAX,
    "equations": EQUATIONS_SYNTAX,
    "sections": SECTIONS_SYNTAX,
}


def describe_syntax(topic: str | None = None) -> str:
    """Return the introductory or topic-specific XHTML syntax reference."""
    if topic is None:
        return XHTML_SYNTAX_OVERVIEW
    return SYNTAX_TOPICS[topic]
